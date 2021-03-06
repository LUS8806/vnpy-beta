# encoding: UTF-8

'''
本文件中包含了CTA模块中用到的一些基础设置、类和常量等。
'''

from __future__ import division


# 把vn.trader根目录添加到python环境变量中
import sys
sys.path.append('..')


# 常量定义
# CTA引擎中涉及到的交易方向类型
CTAORDER_BUY = u'买开'
CTAORDER_SELL = u'卖平'
CTAORDER_SHORT = u'卖开'
CTAORDER_COVER = u'买平'

# 本地停止单状态
STOPORDER_WAITING = u'等待中'
STOPORDER_CANCELLED = u'已撤销'
STOPORDER_TRIGGERED = u'已触发'

# 本地停止单前缀
STOPORDERPREFIX = 'CtaStopOrder.'

# 数据库名称
SETTING_DB_NAME = 'Future_Setting_Db'
POSITION_DB_NAME = 'Future_Position_Db'

TICK_DB_NAME = 'Future_Tick_Db'
DAILY_DB_NAME = 'Future_Daily_Db'
MINUTE_DB_NAME = 'Future_1Min_Db'
MINUTE30_DB_NAME = 'Future_30Min_Db'

# 引擎类型，用于区分当前策略的运行环境
ENGINETYPE_BACKTESTING = 'backtesting'  # 回测
ENGINETYPE_TRADING = 'trading'          # 实盘

# CTA引擎中涉及的数据类定义
from vnpy.trader.vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT
from vnpy.trader.vtObject import VtBarData as CtaBarData
from vnpy.trader.vtObject import VtTickData as CtaTickData


########################################################################
class StopOrder(object):
    """本地停止单"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING
        self.orderType = EMPTY_UNICODE
        self.direction = EMPTY_UNICODE
        self.offset = EMPTY_UNICODE
        self.price = EMPTY_FLOAT
        self.volume = EMPTY_INT
        
        self.strategy = None             # 下停止单的策略对象
        self.stopOrderID = EMPTY_STRING  # 停止单的本地编号 
        self.status = EMPTY_STRING       # 停止单状态
