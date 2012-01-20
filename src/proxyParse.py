# -*- coding: gb2312 -*-
import pycurl
import threading
import urllib2
import urlparse
import sys
import os
import sqlite3
import md5
from sgmllib import SGMLParser


global proxy_data
proxy_data = []



class SqliteData:
    def __init__(self):
        path = os.getcwd() + "./proxy.db"
        self.conn = sqlite3.connect(path)
        self.curs = self.conn.cursor()
        self.curs.execute('CREATE TABLE if not exists proxylist(proxyCurlMd5 TEXT  UNIQUE, proxyCurl TEXT , host VARCHAR(100),port TEXT)')
        self.conn.commit()
        
    def GetMd5(self, data):
        m = md5.new()
        m.update(data)
        return m.hexdigest()
        
    def PutPorxy(self, url=None, port=None):
        if url!=None and port != None:
            proxyCurl = 'http://' + url + ":" + port
            proxyCurlMd5 = self.GetMd5(proxyCurl)
            self.curs.execute('delete from proxylist where proxyCurlMd5=?', [proxyCurlMd5])
            self.curs.execute('insert into proxylist values (?,?,?,?)', [proxyCurlMd5, proxyCurl, url, port])
            
    def UpdateProxy(self, data):
        self.curs.execute('delete from proxylist');
        for i in data:
            proxyCurlMd5 = self.GetMd5(i)
            self.curs.execute('insert into proxylist values (?,?,?,?)', [proxyCurlMd5, i, "", ""])
        
    def Commit(self):
        self.conn.commit()
            
    def GetProxyList(self):
        rs = self.curs.execute("select proxyCurl from proxylist")
        data = []
        for r in rs:
            data.append(r[0])
        return  data
        
    
class CurlGetHtml:
    def __init__(self, url=None, UseCookie=True, dlg=None):
        if url == None:
            return
        self.dlg = dlg
        self.c = pycurl.Curl()
        self.content="" #
        self.url = url
        self.c.setopt(pycurl.VERBOSE, 1)  
        self.c.setopt(pycurl.FOLLOWLOCATION, 1)
        #self.c.setopt(pycurl.PROXY, 'http://www.podjone.com:8080')
        #self.c.setopt(pycurl.MAXREDIRS, 5)  
        self.c.setopt(pycurl.USERAGENT, "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.120 Safari/535.2")
        #self.c.setopt(pycurl.TIMEOUT, 5)
        self.c.setopt(pycurl.URL, url)
        if UseCookie:
            url_base = self.GetUrlBase(url)
            self.c.setopt(pycurl.COOKIEFILE, url_base + "_cookiefile")
            self.c.setopt(pycurl.COOKIEJAR, url_base + "_cookiejar")
        self.c.setopt(pycurl.WRITEFUNCTION, self.writeCallBack)
        self.c.setopt(pycurl.NOPROGRESS, 0)
        self.c.setopt(pycurl.PROGRESSFUNCTION, self.progress)     
        self.fail=False
    
    def progress(self, download_t, download_d, upload_t, upload_d):
        if self.dlg and self.dlg.progress:
            self.dlg.progress(download_t, download_d, upload_t, upload_d)
        
    def writeCallBack(self, buf):
        self.content = self.content + buf
        
    def GetData(self):
        if self.url == None:
            return ""
        try:
            self.c.setopt(pycurl.VERBOSE, 0)
            self.c.perform()
        except:
            self.fail=True
        self.c.close()
        if self.fail:
            return ""
        return self.content
    
    def GetUrlBase(self, url):
        parsedTuple = urlparse.urlparse(url)
        return parsedTuple[1]

class ParseHtmlData(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self.bParse=False
        self.bEnterTr = False
        self.bEnterTd = False
        self.ProxyLists = []
        self.TmpProxyList = []
        self.data = ""
        self.iStep = 0
        
    def start_tr(self, attrs):
        for k, v in attrs:
            if k == 'bgcolor' and v == '#FFFFFF':
                self.bEnterTr = True
                
    def end_tr(self):
        self.bEnterTr = False
        
    def start_td(self, attrs):
        if self.bEnterTr:
            self.bEnterTd = True
                
    def end_td(self):
        if self.bEnterTd:
            self.bEnterTd = False
            self.iStep = self.iStep + 1
            self.TmpProxyList.append(self.data)
            if self.iStep == 4:
                self.iStep = 0
                self.ProxyLists.append(self.TmpProxyList)
                self.TmpProxyList=[]
                
    def handle_data(self, data):
        if self.bEnterTr:
            if data.find('\n') == -1:
                self.data = data
    
    def GetData(self):    
        return self.ProxyLists
    
class ParseHtmlDataHerf(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self.urls = []
        
    def GetDestUrl(self, urls):
        url = urls[0]
        if len(url)<5:
            return ""
        elif url.find('mailto')!=-1:
            return ""
        elif url.find('javascript')!=-1:
            return ""
        elif url.find('www.fjctyz.net')!=-1:
            return ""
        elif url.find('http')!=-1: 
            if url.find('www.fj-pupil.com')!=-1:
                return url
            else:
                return ""
        else:
            return 'http://www.fj-pupil.com/'  + url
        return ""
    
        url = urls[0]
        if url.find('mailto')!=-1:
            return ""
        print url
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
        if len(scheme) == 0:
            # join
            #data = 'http'
            scheme = 'http'
            netloc = 'www.fj-pupil.com'
            return ""
            return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))
        elif netloc.find('www.fj-pupil.com') == -1:
            return ""
        else:
            return url
        
    def start_a(self, attrs):
        href = [v for k, v in attrs if k=='href']
        if href:
            url = self.GetDestUrl(href)
            if len(url)>0:
                self.urls.append(url)
            
    def GetData(self):
        return self.urls
    
    
class Urllib2GetHtml:
    def __init__(self, url=None):
        self.url = url
        self.content=""
        
    def GetData(self):
        if True:
            opener = urllib2.build_opener()
            opener.addheaders =[('User-agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.120 Safari/535.2')]
            u= opener.open(self.url, timeout=5)
            self.content = u.read()
            return self.content
        return self.content

def UpdateProxyData(data):
    proxySqliteData = SqliteData()
    proxySqliteData.UpdateProxy(data)
    proxySqliteData.Commit()
            
def GetProxyData(dlg=None): 
    htmldata_path = os.getcwd() + "./html.data"
    data = ""
    #if os.path.exists(htmldata_path):
    if False:
        f = open(htmldata_path, 'r')
        data = f.read()
        f.close()
    else:
        url = 'http://www.51proxied.com/http_non_anonymous.html'
        c = CurlGetHtml(url)
        CurlGetHtml(c.GetUrlBase(url)).GetData()  # fetch base...
        c = CurlGetHtml(url, dlg = dlg)
        data = c.GetData()
        if len(data) == 0:
            #print "Nothing.."
            return []
        else:
            if os.path.exists(htmldata_path):
                os.remove(htmldata_path)
            f = open(htmldata_path, 'w')
            f.write(data)
            f.close()
            
    # parse data...
    #print "parse data"
    parse_html = ParseHtmlData()
    parse_html.feed(data)
    proxySqliteData = SqliteData()
    for i in parse_html.GetData():
        proxySqliteData.PutPorxy(i[1], i[2])
    proxySqliteData.Commit()
    proxy_data = proxySqliteData.GetProxyList()
    return proxy_data

def GetProxyDataFromSqlite(dlg=None):
    proxySqliteData = SqliteData()
    proxy_data = proxySqliteData.GetProxyList()
    return proxy_data

if __name__ == '__main__':
    url = 'http://www.fj-pupil.com/portal.php?mod=list&catid=4'
    htmldata_path = os.getcwd() + "./html.data"
    if os.path.exists(htmldata_path) == False:   
        c = CurlGetHtml(url)
        data = c.GetData()
        f = open(htmldata_path, 'w')
        f.write(data)
        f.close()
    else:
        f = open(htmldata_path, 'r')
        data = f.read()
        f.close()
        
    if len(data)>0:
        parse = ParseHtmlDataHerf()
        parse.feed(data)
        for i in parse.GetData():
            print i
        
    pass

    

    
    