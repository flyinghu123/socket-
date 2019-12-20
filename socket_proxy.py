# -*- coding: utf-8 -*-
# @Date    : 2019-12-20 00:26:05
# @Author  : Flying Hu (1152598046@qq.com)
# @Link    : http://www.flyinghu.cn
# @Version : 0.1


import socket
from urllib.parse import urlparse
# import chardet
# from pprint import pprint as print
# 全篇使用requests模块使用http代理测试


def proxy(client_socket):
    '''代理客户端socket'''
    # 1.接收客户端发送的消息
    recv_data = b''
    while True:
        tmp_data = client_socket.recv(1024)
        recv_data += tmp_data
        if len(tmp_data) < 1024:
            # 当接收到的消息小于应该接收的长度表示读取结束
            # 本人测试使用if tmp_data判断时， 因为使用此判断会再一次调用recv函数读取, 然后会造成客户端使用requests使用代理时会获取不到数据
            break
    # 分析请求头
    headers = analysis_head(recv_data.decode().split('\r\n\r\n', 1)[0])
    # 模拟请求向目标发送请求获取数据
    send_data = get_target_data(headers, recv_data.decode().split('\r\n\r\n', 1)[1])
    # 添加Content-Length请求头否则requests无法接收数据
    head_data = send_data.decode('utf-8', errors='replace').split('\r\n\r\n', 1)[0]
    body_data = send_data.decode('utf-8', errors='replace').split('\r\n\r\n', 1)[1].encode('utf-8')
    # 使用fstring拼接
    head_data += '\r\n' + f'Content-Length: {len(body_data)}' + '\r\n\r\n'
    send_data = head_data.encode('utf-8') + body_data
    # 发送数据
    cut_send(client_socket, send_data)
    # client_socket.sendall(send_data)


def analysis_head(head_data):
    '''分析请求头
    Args:
        head_data 原始请求头信息
    Return:
        headers 解析后的请求头字典
    '''
    # 使用\r\n将原始请求头分隔成字典
    head_list = head_data.split('\r\n')
    # 分隔出请求方式, 请求url, 协议
    method, url, protocol = head_list[0].split(' ')[0], head_list[0].split(' ')[1], head_list[0].split(' ')[2].split('/')[0]
    headers = {}
    url = urlparse(url)
    headers['method'] = method
    headers['target_url'] = url
    headers['protocol'] = protocol
    for _ in head_list[1:]:
        key, value = _.split(':', 1)[0].strip(), _.split(':', 1)[1].strip()
        headers[key] = value
    return headers


def get_target_data(headers, body):
    '''获取目标网站数据
    Args:
        headers 解析后的header字典
        body 请求体
    Return:
        recv_data 目标网站数据
    '''
    # 创建目标网站客户端socket
    target_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 获取连接端口号
    if len(headers.get('Host').split(':')) > 1:
        port = int(headers.get('Host').split(':')[1])
    elif headers.get('protocol') == 'HTTP':
        port = 80
    else:
        port = 443
    # 连接目标网站
    target_client.connect((socket.gethostbyname(headers.get('Host').split(':', 1)[0]), port))
    # 拼接基础请求头
    body = body.encode('utf-8')
    tmp_data = f"{headers.get('method')} {headers.get('target_url').path} {headers.get('protocol')}/1.1\r\nPragma: no-cache\r\nConnection: close\r\nContent-Length: {len(body)}\r\n"
    del headers['method']
    del headers['protocol']
    del headers['target_url']
    # 遍历字典添加请求头
    for key, value in headers.items():
        tmp_data += f"{key}: {value}\r\n"
    tmp_data += "\r\n"
    # 设置超时
    target_client.settimeout(2)
    # 发送数据
    cut_send(target_client, (tmp_data.encode() + body))
    # target_client.sendall((tmp_data.encode() + body))
    # 接收目标网站数据
    recv_data = b''
    tmp_data = b''
    while True:
        tmp_data = target_client.recv(1024)
        if tmp_data:
            recv_data += tmp_data
        else:
            break
        # if len(tmp_data) < 1024:
        # 这里使用该判断出错
        #     break
    if not recv_data:
        # 未接收到数据
        # print('空数据')
        pass
    target_client.close()
    return recv_data


def cut_send(client_socket, data, length=1024):
    for i in range(int(len(data)/length) + 1):
        tmp = data[i*length:length*(i + 1)]
        client_socket.send(tmp)


if __name__ == "__main__":
    ip = '127.0.0.1'  # 代理绑定的ip
    port = 1080  # 绑定的端口号
    # 创建服务socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 设置端口复用
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 绑定ip和端口
    server_socket.bind((ip, port))
    # 监听
    server_socket.listen(128)
    # 开启服务死循环
    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(addr)
            try:
                # 代理
                proxy(client_socket)
            except Exception as e:
                # 打印可能的异常
                print(repr(e), e.__traceback__.tb_lineno, '行')
            finally:
                # close客户端socket
                client_socket.close()
    except KeyboardInterrupt:
        # 捕获 CTRL + C
        print('手动停止')
    except Exception as e:
        # 捕获其他异常
        print(e)
    finally:
        server_socket.close()
