# -*- coding: gb2312 -*-  
import wx
import os
import sys
import Queue
import threading
import urllib2
import time
import pycurl
import wx.gizmos
import urlparse

import proxyParse
from wxPython._misc import wxMessageBox

g_queue = Queue.Queue()
g_dlg = None
g_lock = threading.Lock()
#g_lock_thread_num = threading.Lock()
#g_lock_refresh_num = threading.Lock()
g_lock_thread_num = threading.Semaphore()
g_lock_refresh_num = threading.Semaphore()
global g_thread_resfresh 
global g_thread_num
global g_thread_num_max
global g_refresh_times
global g_refresh_exit
g_thread_resfresh = None
g_thread_num=0
g_thread_num_max=100
g_refresh_times=0
g_refresh_times_max=0
g_refresh_exit=False # 控制刷新进程退出
g_log_str=None
global proxyData
proxyData = []   # 代理列表

def LOG(logstr):
    global g_log_str
    g_lock.acquire()
    #g_dlg.log(logstr)
    g_log_str = logstr
    g_lock.release()
    
def SetThreadNum(step=1):
    global g_thread_num 
    g_lock_thread_num.acquire()
    g_thread_num = g_thread_num + step
    g_lock_thread_num.release()
    
def GetThreadNum():
    global g_thread_num 
    g_lock_thread_num.acquire()
    v = g_thread_num 
    g_lock_thread_num.release()
    return v

def SetRefreshNum(step=1):
    global g_refresh_times
    g_lock_refresh_num.acquire()
    g_refresh_times = g_refresh_times + step
    g_lock_refresh_num.release()
    
def GetRefreshNum():
    global g_refresh_times
    g_lock_refresh_num.acquire()
    v = g_refresh_times
    g_lock_refresh_num.release()
    return v

global proxyitem
proxyitem = 0
'''
 获取代理地址
'''
def GetProxyHttp():
    global proxyData
    global proxyitem
    if len(proxyData) == 0:
        return ""
    if proxyitem >= len(proxyData):
        proxyitem = 1
    else:
        proxyitem += 1
        
    return proxyData[proxyitem]

'''
移除代理有误的地址
'''
def RemoveProxyHttp(html):
    proxyData.remove(html)

        

class ThreadRfershLog(threading.Thread):
    def run(self):
        global g_log_str
        global g_refresh_exit
        global g_refresh_times
        global g_refresh_times_max
        while g_refresh_exit==False:
            if g_log_str:
                g_dlg.log(g_log_str)
            g_dlg.Info("已刷新:%d 需刷新:%d" % (g_refresh_times, g_refresh_times_max))
            g_dlg.static_ProxyInfo.SetLabel('可用代理地址总数:%d' % len(proxyData))
            time.sleep(1)       
            
class ThreadRefresh(threading.Thread):
    def __init__(self, url, bProxy=False):
        threading.Thread.__init__(self)
        self.url = url
        self.bProxy = bProxy
        self.bFirstEnter = False
        self.content = ""
        self.proxyHttp = ""
        
    def write_callback(self, buf):
        #self.content += buf
        #return
        if self.bFirstEnter == True:
            self.bFirstEnter = False
            return 0
        else:
            self.bFirstEnter = True
    
    def run(self):
        global g_refresh_times_max
        global g_thread_num
        SetThreadNum(1)
        host = self.url
        start = time.time()
        c = pycurl.Curl()
        try:
            c.setopt(pycurl.URL, host)
            c.setopt(pycurl.USERAGENT, "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.120 Safari/535.2")
            c.setopt(pycurl.WRITEFUNCTION, self.write_callback)
            if self.bProxy:
                self.proxyHttp = str(GetProxyHttp())
               
                c.setopt(pycurl.PROXY, self.proxyHttp)
            c.setopt(pycurl.TIMEOUT, 5)
            c.perform()                  
            SetRefreshNum(1)
            if False:
                path = os.getcwd()+'.\\data\\'
                if os.path.exists(path) == False:
                    os.mkdir(path)
                path =  path + "data.html"
                if os.path.exists(path):
                    os.remove(path)
                f = open(path, 'w')
                f.write(self.content)
                f.close()
                
            #LOG("Elapsed Time: %s" % (time.time() - start))
            
        except pycurl.error, e:
            #print e[0]
            if e[0] == pycurl.E_WRITE_ERROR:
                if self.bProxy:
                    g_dlg.Log(self.proxyHttp + "   ok...")
                SetRefreshNum(1)
            else:#if e[0] == pycurl.E_COULDNT_CONNECT:
                if self.bProxy:
                    g_dlg.Log(self.proxyHttp + "   fail..")
                    RemoveProxyHttp(self.proxyHttp)
        c.close()
        SetThreadNum(-1)
        #LOG("Thread[%s] Run:%8d Max:%8d RefreshNum:%8d RfreshMax:%8d" % (self.getName(), g_thread_num, g_thread_num_max, g_refresh_times, g_refresh_times_max))
        
def StartNewRefreshThread(url, bProxy=False):                
    while GetThreadNum() > g_thread_num_max:
        time.sleep(0.01)
    time.sleep(0.01)
    try:
        refresh_thread = ThreadRefresh(url, bProxy)
        refresh_thread.start()
    except threading.ThreadError, e:
        LOG("Start Trhead fail...")
                
class ThreadManager(threading.Thread):
    def __init__(self, url=None, times=1000000, bProxy=False):
        threading.Thread.__init__(self)
        global g_refresh_times_max
        self.url = url
        self.times = times
        self.bProxy = bProxy
        g_refresh_times_max = times

    def run(self):
        global g_refresh_exit
        g_refresh_exit=False
        while GetRefreshNum() < self.times:
            StartNewRefreshThread(self.url, self.bProxy)
            if g_refresh_exit:
                while GetThreadNum()>0:
                    time.sleep(1)
                g_dlg.OnEndRefresh()
                return
        g_dlg.OnEndRefresh()
    
class ShuaShuaFrame(wx.Frame):
    g_dbgTimes=0
    """Main Frame holding the Panel."""
    def __init__(self, *args, **kwargs):
        """Create the DemoFrame."""
        wx.Frame.__init__(self, *args, **kwargs)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # menubar
        menuBar = wx.MenuBar()
        menu = wx.Menu()
        menu_refreshDlg = menu.Append(-1, "刷刷", "打开刷刷")
        menu_proxyDlg = menu.Append(-1, "获取代理", "获取代理")
        self.Bind(wx.EVT_MENU, self.OnRfreshDlg, menu_refreshDlg)
        self.Bind(wx.EVT_MENU, self.OnProxyDlg, menu_proxyDlg)
        
        # static
        l = '基友新年快乐!!!!!!!!\n'
        for i in range(10):
            l += l
        static_info = wx.StaticText(self, label=l, style=wx.ALIGN_CENTRE)
        static_info.SetFont(wx.Font(30, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        vbox.Add(static_info, -1, wx.EXPAND|  wx.TOP | wx.BOTTOM, 10)
        
        menuBar.Append(menu, "操作")
        self.SetMenuBar(menuBar)
        
        self.SetSizer(vbox)
        self.SetAutoLayout(1)
        #vbox.Fit(self)
        
        self.Center()
        #self.Maximize()
        
    def OnRfreshDlg(self, event):
        dlg = RefreshDlg()
        dlg.ShowModal()
        dlg.Destroy()
    
    def OnProxyDlg(self, event):
        dlg = ProxyDlg()
        dlg.ShowModal()
        dlg.Destroy()
    
class ThreadGetProxyData(threading.Thread):
    def __init__(self, dlg=None):
        threading.Thread.__init__(self)
        self.dlg = dlg
        self.bReport = True

    def run(self):
        global proxyData
        proxyData = proxyParse.GetProxyData(self)
        if self.bReport:
            self.dlg.OnGetProxyFinsh()
        
    def progress(self, download_t, download_d, upload_t, upload_d):
        if self.bReport:
            self.dlg.Info('下载中 %d'% (download_d))
            #print download_t, download_d, upload_t, upload_d

class RefreshDlg(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, -1, '刷刷', size=(600, 600))
        vboxMain = wx.BoxSizer(wx.VERTICAL)
        
        # box
        StaticBox = wx.StaticBox(self, -1, "")
        StaticBoxSize = wx.StaticBoxSizer(StaticBox, wx.VERTICAL)

        # edit url
        hboxTmp = wx.BoxSizer(wx.HORIZONTAL)
        StaticBoxSize.Add(hboxTmp, 0, wx.EXPAND, 5)
        hboxTmp.Add(wx.StaticText(self, wx.ID_ANY, "刷新网页:"))
        self.edit_Url = wx.TextCtrl(self, style = wx.TE_AUTO_URL)
        self.edit_Url.SetLabel('http://www.fj-pupil.com/article-26546-1.html')
        hboxTmp.Add(self.edit_Url, -1, wx.EXPAND, 5)
        
        # edit num
        hboxTmp = wx.BoxSizer(wx.HORIZONTAL)
        StaticBoxSize.Add(hboxTmp, 0, wx.EXPAND, 5)
        self.edit_Num = wx.TextCtrl(self)
        self.edit_Num.SetLabel("100")
        hboxTmp.Add(wx.StaticText(self, wx.ID_ANY, "刷新次数:"))
        hboxTmp.Add(self.edit_Num, 0, wx.EXPAND, 5)
        
        # edit Refresh Thread Num
        hboxTmp = wx.BoxSizer(wx.HORIZONTAL)
        StaticBoxSize.Add(hboxTmp, 0, wx.EXPAND, 5)
        self.edit_ThreadNum = wx.TextCtrl(self)
        self.edit_ThreadNum.SetLabel("20")
        hboxTmp.Add(wx.StaticText(self, wx.ID_ANY, "线程数:   "))
        hboxTmp.Add(self.edit_ThreadNum, 0, wx.EXPAND, 5)
        
        # btn Refresh
        self.btn_Refresh = wx.Button(self, wx.ID_ANY, "刷新")
        self.Bind(wx.EVT_BUTTON, self.OnBtnRefresh, self.btn_Refresh)
        StaticBoxSize.Add(self.btn_Refresh, 0, wx.ALL, 5)
        
        # checkbox proxy
        self.checkbox_Proxy = wx.CheckBox(self, -1,  '是否代使用代理')
        self.checkbox_Proxy.SetValue(False)
        StaticBoxSize.Add(self.checkbox_Proxy, 0, wx.ALL, 5)
                                           
        # static info
        self.static_Info = wx.StaticText(self, wx.ID_ANY, "这里输出刷新信息")
        StaticBoxSize.Add(self.static_Info, 0, wx.ALL, 5)
        
        # proxy info
        self.static_ProxyInfo = wx.StaticText(self, wx.ID_ANY, "Proxy Info")
        StaticBoxSize.Add(self.static_ProxyInfo, 0, wx.ALL, 5)

        # dbg info
        self.dbg_control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        StaticBoxSize.Add(self.dbg_control, -1, wx.EXPAND, 5)
                
        # sizer...
        vboxMain.Add(StaticBoxSize, -1, wx.EXPAND)
        self.SetSizer(vboxMain)
        self.SetAutoLayout(1)      
        self.Center()
        
        # load data
        global proxyData
        proxyData = proxyParse.GetProxyDataFromSqlite()
        self.static_ProxyInfo.SetLabel('可用代理地址总数:%d' % len(proxyData))
        
        global g_dlg
        g_dlg = self
        
        # lock
        self.log_lock = threading.Lock()
        
        # event
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.thread_mgr = None
        
        
    def OnClose(self, event):
        if self.thread_mgr!=None:
            wxMessageBox("线程工作中无法退出!")
        else:
            self.Destroy()
        
    def OnBtnRefresh(self, event):
        global g_thread_num_max
        global g_refresh_times_max
        global g_refresh_times
        global g_refresh_exit
        g_refresh_exit = False
        g_refresh_times = 0
        g_thread_num_max = int(self.edit_ThreadNum.GetLabel())
        g_refresh_times_max = int(self.edit_Num.GetLabel())
        bProxy = self.checkbox_Proxy.GetValue()
        self.dbg_control.SetLabel('')
        
        self.thread_timer = ThreadRfershLog()
        self.thread_timer.start()
        
        self.thread_mgr = ThreadManager(url=self.edit_Url.GetLabel(), times=g_refresh_times_max, bProxy = bProxy)
        self.thread_mgr.start()
        
        self.btn_Refresh.Enable(False)
        self.Info("刷新ing...")
        
    def Log(self, data):
        self.log_lock.acquire()
        if len(data)>0 :
            self.dbg_control.AppendText(str(data) + '\n')
        self.log_lock.release()
        
    def log(self, data):
        #print data
        #self.Log(data)
        if len(data)>0 :
            self.dbg_control.AppendText(str(data) + '\n')
        
    def Info(self, data):
        self.static_Info.SetLabel(data) 
        
    def OnStopRefresh(self, event):
        global g_refresh_exit
        g_refresh_exit = True
        self.log("等待线程退出")
        
    def OnEndRefresh(self):
        global g_refresh_exit
        global g_refresh_times
        global proxyData
        self.Info("已刷新:%d 需刷新:%d" % (g_refresh_times, g_refresh_times_max))
        g_refresh_times = 0
        self.thread_mgr = None
        g_refresh_exit = True
        self.log("线程已退出")
        self.btn_Refresh.Enable(True)
        proxyParse.UpdateProxyData(proxyData)
        
            
class ProxyDlg(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, -1, '代理列表', size=(600, 600))
        vboxMain = wx.BoxSizer(wx.VERTICAL)
         
        # box
        StaticBox = wx.StaticBox(self, -1, "代理列表")
        StaticBoxSize = wx.StaticBoxSizer(StaticBox, wx.VERTICAL)
        
        # btn Fetch 
        hboxBtn = wx.BoxSizer(wx.HORIZONTAL)
        StaticBoxSize.Add(hboxBtn, 0, wx.ALL, 5)
        
        self.btn_GetProxy = wx.Button(self, wx.ID_ANY, "获取代理列表")
        self.Bind(wx.EVT_BUTTON, self.OnGetProxy, self.btn_GetProxy)
        hboxBtn.Add(self.btn_GetProxy, 0, wx.ALL, 5)
        
        # btn Load
        self.btn_Load = wx.Button(self, wx.ID_ANY, "从数据库读取")
        self.Bind(wx.EVT_BUTTON, self.OnLoadProxy, self.btn_Load)
        hboxBtn.Add(self.btn_Load, 0, wx.ALL, 5)
        
        # static info
        self.static_Info = wx.StaticText(self, wx.ID_ANY, "INFO")
        StaticBoxSize.Add(self.static_Info, 0, wx.ALL, 5)
        
        # list
        self.treeList_Proxy = wx.gizmos.TreeListCtrl(self, style=wx.TR_DEFAULT_STYLE | wx.TR_FULL_ROW_HIGHLIGHT)
        self.treeList_Proxy.AddColumn("Num")
        self.treeList_Proxy.AddColumn("Proxy")
        self.treeList_Proxy.SetColumnWidth(0, 100)
        self.treeList_Proxy.SetColumnWidth(1, 800)
        StaticBoxSize.Add(self.treeList_Proxy, -1, wx.EXPAND, 5)
        self.root = self.treeList_Proxy.AddRoot("Proxy")
        self.treeList_Proxy.Expand(self.root)
        
        # sizer...
        vboxMain.Add(StaticBoxSize, -1, wx.EXPAND)
        self.SetSizer(vboxMain)
        self.SetAutoLayout(1)      
        self.Center()
        
        # threading..
        self.threadProxy = None
        
    def OnGetProxy(self, event):
        if self.threadProxy:
            self.Info('已停止获取代理列表...')
            self.btn_GetProxy.SetLabel('获取代理列表')
            self.threadProxy.bReport = False
            self.threadProxy = None
        else:
            self.Info('获取代理列表中...')
            self.btn_GetProxy.SetLabel('停止获取')
            self.threadProxy = ThreadGetProxyData(self)
            self.threadProxy.start()
            
    def OnLoadProxy(self, event):
        proxyData = proxyParse.GetProxyDataFromSqlite()
        self.treeList_Proxy.DeleteAllItems()
        self.root = self.treeList_Proxy.AddRoot("Proxy")
        num = 0
        self.Info("正在加载...")
        for i in proxyData:
            num += 1
            newitem = self.treeList_Proxy.AppendItem(self.root, str(num))
            self.treeList_Proxy.SetItemText(newitem, i, 1)
        self.treeList_Proxy.Expand(self.root)
        self.Info("加载结束....")
        
    def Info(self, data):
        self.static_Info.SetLabel(data)
        
    def OnGetProxyFinsh(self):
        global proxyData
        num = 0
        self.treeList_Proxy.DeleteAllItems()
        self.root = self.treeList_Proxy.AddRoot("Proxy")
        for i in proxyData:
            num += 1
            newitem = self.treeList_Proxy.AppendItem(self.root, str(num))
            self.treeList_Proxy.SetItemText(newitem, i, 1)
        self.treeList_Proxy.Expand(self.root)
        self.threadProxy = None
        self.btn_GetProxy.SetLabel('获取代理列表')
        self.Info("获取结束")
    
if __name__ == '__main__':
    app = wx.App(False)
    frame = ShuaShuaFrame(None, title="刷到底....", size=(600, 600))
    #g_dlg = frame
    frame.Show()
    #frame.OnProxyDlg(None)
    frame.OnRfreshDlg(None)
    app.MainLoop()
    #g_refresh_exit = True    
