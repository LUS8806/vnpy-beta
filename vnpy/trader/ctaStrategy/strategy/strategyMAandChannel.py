# encoding: UTF-8

"""
均线和通道结合的交易策略, 基于30分钟K线

"""

import talib
import numpy as np
import time

from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.ctaStrategy.ctaTemplate import CtaTemplate
from vnpy.trader.vtObject import VtBarData as CtaBarData

########################################################################
class MAandChannelStrategy(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'MAandChannelStrategy'
    author = u'Song'

    # 策略参数
    chnelLength = 20 # 计算通道的窗口数
    maLength = 20

    initDays = 10  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量

    # 策略变量
    bar = None  # K线对象
    lastTickTime = None  #上一个tick的时间
    lastBarMinute = None  #上一根k线的时间　

    bufferSize = 100  # 需要缓存的数据的大小
    bufferCount = 0  # 目前已经缓存了的数据的计数
    tickCount = 0
    highArray = np.zeros(bufferSize)  # K线最高价的数组
    lowArray = np.zeros(bufferSize)  # K线最低价的数组
    closeArray = np.zeros(bufferSize)  # K线收盘价的数组
    maArray = np.zeros(4)


    orderList = []  # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'chnelLength',
                 'maLength']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               ]

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MAandChannelStrategy, self).__init__(ctaEngine, setting)

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算k线
        tickDatetime = tick.datetime
        tickMinute = tickDatetime.minute

        # 过滤无效tick
        if tick.volume == 0:
            return

        if self.tickCount == 0:
            lastTickTime = tickDatetime
        else:
            lastTickTime = self.lastTickTime

        self.lastTickTime = tickDatetime
        self.tickCount += 1

        if tickMinute % 30 > 0:
            if self.bar: #TODO bar下面加了一个字段
                bar = self._updateBar(tick)
            else:
                bar = self._creatNewBar(tick)
        elif tickMinute % 30 == 0:
            if self.bar:
                if lastTickTime.minute % 30 == 0:
                    bar = self._updateBar(tick)
                else:
                    self.bar.finished = True
                    self.onBar(self.bar)
                    bar = self._creatNewBar(tick)
            else:
                bar = self._creatNewBar(tick)
        self.bar = bar
        self.onBar(bar)

    def _creatNewBar(self, tick):
        """创建新k线"""
        bar = CtaBarData()
        bar.vtSymbol = tick.vtSymbol
        bar.symbol = tick.symbol
        bar.exchange = tick.exchange

        bar.open = tick.lastPrice
        bar.high = tick.lastPrice
        bar.low = tick.lastPrice
        bar.close = tick.lastPrice

        bar.date = tick.date
        bar.time = tick.time
        bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间
        return bar

    def _updateBar(self, tick):
        """更新当前K线"""
        bar = self.bar
        bar.close = tick.lastPrice
        bar.high = max(bar.high, tick.lastPrice)
        bar.low = min(bar.low, tick.lastPrice)
        return bar

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到30分钟K线"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

        # TODO 这里有问题，每个tick都调用OnBar
        self.closeArray[0:self.bufferSize - 1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize - 1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize - 1] = self.lowArray[1:self.bufferSize]

        self.closeArray[-1] = bar.close
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low

        self.bufferCount += 1
        if self.bufferCount < self.bufferSize:
            return

        # 计算指标数值
        self.maArray = talib.MA(self.closeArray, self.maLength)[-5:-1]
        # 判断是否要进行交易
        maConLong = self.maArray[0] < self.maArray[1] < self.maArray[2] < self.maArray[3]
        maConShort = self.maArray[0] > self.maArray[1] > self.maArray[2] > self.maArray[3]
        HH = max(self.highArray[-1*self.chnelLength:-1])
        LL = min(self.lowArray[-1*self.chnelLength:-1])
        crossOverH = bar.high > HH
        crossUnderL = bar.low < LL

        if crossOverH and maConLong:
            targetPrice = max(HH, bar.open)
            if self.pos == 0:
                self.buy(targetPrice, self.fixedSize)
            elif self.pos < 0:
                self.cover(targetPrice, abs(self.pos))
                self.buy(targetPrice, self.fixedSize)

        elif crossUnderL and maConShort:
            targetPrice = min(LL, bar.open)
            if self.pos == 0:
                self.short(targetPrice, self.fixedSize)
            elif self.pos > 0:
                self.sell(targetPrice, self.pos)
                self.short(targetPrice, self.fixedSize)

        # 发出状态更新事件
        self.putEvent()

        # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()


if __name__ == '__main__':
    # 提供直接双击回测的功能
    # 导入PyQt4的包是为了保证matplotlib使用PyQt4而不是PySide，防止初始化出错
    from ctaBacktesting import *
    from PyQt4 import QtCore, QtGui

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20120101')

    # 设置产品相关参数
    engine.setSlippage(0.2)  # 股指1跳
    engine.setRate(0.3 / 10000)  # 万0.3
    engine.setSize(10)  # 股指合约大小
    engine.setPriceTick(0.2)  # 股指最小价格变动

    # 设置使用的历史数据库
    engine.setDatabase(MINUTE30_DB_NAME, 'rb888')

    # 在引擎中创建策略对象
    d = {'atrLength': 11}
    engine.initStrategy(MAandChannelStrategy, d)

    # 开始跑回测
    engine.runBacktesting()

    # 显示回测结果
    engine.showBacktestingResult()

    ## 跑优化
    # setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    # setting.setOptimizeTarget('capital')            # 设置优化排序的目标是策略净盈利
    # setting.addParameter('atrLength', 12, 20, 2)    # 增加第一个优化参数atrLength，起始11，结束12，步进1
    # setting.addParameter('atrMa', 20, 30, 5)        # 增加第二个优化参数atrMa，起始20，结束30，步进1
    # setting.addParameter('rsiLength', 5)            # 增加一个固定数值的参数

    ## 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
    ## 测试时还跑着一堆其他的程序，性能仅供参考
    # import time
    # start = time.time()

    ## 运行单进程优化函数，自动输出结果，耗时：359秒
    # engine.runOptimization(AtrRsiStrategy, setting)

    ## 多进程优化，耗时：89秒
    ##engine.runParallelOptimization(AtrRsiStrategy, setting)

    # print u'耗时：%s' %(time.time()-start)