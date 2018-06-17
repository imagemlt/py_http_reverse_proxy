#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# File Name: HighPerformanceServer.py
# Author: Image
# mail: malingtao1019@163.com
# Blog:http://blog.imagemlt.xyz
# Created Time: 2018年06月16日 星期六 17时00分01秒
import sys
import socket
import time
import gevent
import json
from gevent import socket,monkey
monkey.patch_all()
import os


def server(config):
    s=socket.socket()
    s.bind((config['listen_host'],config['listen_port']))
    s.listen(65535)
    pids=[]
    isMaster=True
    for i in range(0,10):
       pid=os.fork()
       if(pid==0):
           isMaster=False 
           break
       else:
           pids.append(pid)
    if(isMaster):
        print "I am master"
        print pids
    while True:
            cli,addr=s.accept()
            gevent.spawn(handle_request,cli,addr,config)

def parse_client_header(header_chunk):
    lines=header_chunk.split('\r\n')
    headers={}
    for line in lines[1:]:
        key,value=line.split(':',1)
        headers[key.strip().lower()]=value.strip()
    query_message=lines[0].split(' ')
    queryinfo={'method':query_message[0],'url':query_message[1],'version':query_message[2]}
    return queryinfo,headers
    
def parse_server_header(header_chunk):
    lines=header_chunk.split('\r\n')
    headers={}
    for line in lines[1:]:
        key,value=line.split(':',1)
        headers[key.strip().lower()]=value.strip()
    responce_message=lines[0].split(' ')
    responce_info={'version':responce_message[0],'code':responce_message[1],'message':responce_message[2]}
    return responce_info,headers 

def handle_request(conn,addr,config):
    try:
        print "recived request from %s:%s"%(addr[0],addr[1])
        connserver=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        connserver.connect((config['remote_host'],config['remote_port']))
        header_recived=False 
        cli_size=0
        recived_size=0
        cli_chunked=False 
        while True:
            data=conn.recv(1024)
            if not data:
                conn.shutdown(socket.SHUT_WR)
            if not header_recived:
                cliheader=data.split('\r\n\r\n')
                if(len(cliheader)!=2):
                    break
                reqinfo,reqheaders=parse_client_header(cliheader[0])
                print reqinfo
                if reqinfo['method']=='POST' or reqinfo['method']=='PUT':
                    if reqheaders.has_key("transfer-encoding") and reqheaders['transfer-encoding']=="chunked":
                        cli_chunked=True
                        header_reviced=True 
                        if "0\r\n\r\n" in cli_chunked:
                            header_recived=False
                    elif reqheaders['content-length']:
                        cli_size=int(reqheaders['content-length'])
                        recived_size+=len(cliheader[1])
                        if(recived_size>=cli_size):
                            header_recived=False
                        else:
                            header_recived=True 
            else:
                if(cli_chunked):
                    if "0\r\n\r\n" in data:
                        header_recived=False 
                else:
                    recived_size+=len(data)
                    if recived_size>=cli_size:
                        header_recived=False 
                
            print "recv:"+data
            connserver.send(data)
            if(header_recived):
                continue 
            data=connserver.recv(1024)
            message=data.split('\r\n\r\n')
            responce_info,responce_headers=parse_server_header(message[0])
            res_chunked=False
            res_size=0
            res_recived_size=0
            #print responce_headers
            if responce_headers.has_key('transfer-encoding') and responce_headers['transfer-encoding']=='chunked':
                res_chunked=True
            elif responce_headers['content-length']:
                res_size=int(responce_headers['content-length'])
                res_recived_size=len(message[1])
            while(True):
                if res_chunked:
                    if '0\r\n\r\n' in data:
                        break
                else:
                    if res_recived_size>=res_size:
                        break 
                conn.send(data)
                data=connserver.recv(1024)
                res_recived_size+=len(data)
                #print res_recived_size
                
            conn.send(data)
            if responce_headers['connection']=='close':
                conn.shutdown(socket.SHUT_WR)
            print "ended a transaction"
    except Exception as ex:
        print ex.message
    finally:
        conn.close()
        connserver.close()
        print "disconnected with %s:%s"%(addr[0],addr[1])

if __name__=='__main__':
    config=json.loads(open('config.json').read())
    server(config)
