#!/usr/bin/python3.7.0
# -*- coding: utf-8 -*-
import requests
import base64
import re
import time
from lxml import etree
import threading
import queue


class CX:
    # 实例化请传入手机号和密码
    def __init__(self, phonenums, password):
        self.acc = phonenums 
        self.pwd = password
        self.mappid = None
        self.incode = None
        self.deptIdEnc = None
        self.room = None
        self.deptId = None
        self.room_id_name = {}
        self.room_id_capacity = {}
        self.all_seat = []
        self.db = {
            'sb': 0,
            'nb': 0
        }
        self.session = requests.session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 '
                          '(KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
        }
        self.login()                    # 第一步 必须
        self.status = {
            '0': '待履约',
            '1': '学习中',
            '2': '已履约',
            '3': '暂离中',
            '5': '被监督中',
            '7': '已取消',
        }
        self.get_fidEnc()               # 第二步 必须
        self.get_all_room_and_seat()    # 这一步看需求 非必须

    # 获取cookies 
    def login(self):
        c_url = 'https://passport2.chaoxing.com/mlogin?' \
                'loginType=1&' \
                'newversion=true&fid=&' \
                'refer=http%3A%2F%2Foffice.chaoxing.com%2Ffront%2Fthird%2Fapps%2Fseat%2Findex'
        self.session.get(c_url).cookies.get_dict()
        data = {
            'fid': '-1',
            'uname': self.acc,
            'password': base64.b64encode(self.pwd.encode()).decode(),
            'refer': 'http%3A%2F%2Foffice.chaoxing.com%2Ffront%2Fthird%2Fapps%2Fseat%2Findex',
            't': 'true'
        }
        self.session.post('https://passport2.chaoxing.com/fanyalogin', data=data)
        s_url = 'https://office.chaoxing.com/front/third/apps/seat/index'
        self.session.get(s_url)

    # 身份获取 官方的接口 自行研究
    def get_role(self):  
        role = self.session.get(url='https://office.chaoxing.com/data/apps/seat/person/role').json()
        # print(role)
        try:
            for index in role['data']['roleList']['data']:
                if role['data']['roleListSelf'][0]['roleId'] == index['roleid']:
                    myRole = index['roleName']  # 身份
                    print(myRole)
                    break
        except KeyError:
            print('服务器未响应正确值，请重试')

    # 无聊的信息
    def get_wx(self):
        reserve_wx_config = self.session.post(url='https://office.chaoxing.com/data/apps/reserve/wx/config').json()
        seatIndex = self.session.get(url='https://office.chaoxing.com/data/apps/seat/index').json()
        seatConfig = self.session.get(url='https://office.chaoxing.com/data/apps/seat/config').json()
        # print(reserve_wx_config)
        # print(seatIndex)
        # print(seatConfig)

    # 获取学校id
    def get_fidEnc(self):
        data = {
            'searchName': '',
            '_t': self.get_date()
        }
        res = self.session.post(url='https://i.chaoxing.com/base/cacheUserOrg', data=data)
        print(res.json()["site"][0]['schoolname'], res.json()["site"][1]['schoolname'])
        for index in res.json()["site"]:
            fid = index['fid']
            res = self.session.get(url='https://uc.chaoxing.com/mobileSet/homePage?'
                                       f'fid={fid}')
            selector = etree.HTML(res.text)
            mappid = selector.xpath('/html/body/div[1]/div[3]/ul/li[1]/@onclick')
            if mappid:
                self.mappid = mappid[0].split('(')[1].split(',')[0]
        self.incode = self.session.cookies.get_dict()['wfwIncode']
        url = f'https://v1.chaoxing.com/mobile/openRecentApp?incode={self.incode}&mappId={self.mappid}'
        res = self.session.get(url=url, allow_redirects=False)
        self.deptIdEnc = re.compile("fidEnc%3D(.*?)%").findall(res.headers['Location'])[0]

    # 获全部预约记录
    def get_seat_reservation_info(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/reservelist?'
                                        'indexId=0&'
                                        'pageSize=100&'
                                        'type=-1').json()['data']['reserveList']
        print(response)
        for index in response:
            if index['type'] == -1:
                print(index['seatNum'], index['id'], index['firstLevelName'], index['secondLevelName'],
                      index['thirdLevelName'], self.t_time(index['startTime']), self.t_time(index['endTime']),
                      self.t_second(index['learnDuration']), self.status[str(index['status'])])
            else:
                print(index['seatNum'], index['id'], index['firstLevelName'], index['secondLevelName'],
                      index['thirdLevelName'], self.t_time(index['startTime']), self.t_time(index['endTime']),
                      self.t_second(index['learnDuration']), '违约')

    # 签到
    def sign(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/sign?'
                                        f'id={self.get_my_seat_id()}')
        print(response.json())

    # 暂离
    def leave(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/leave?'
                                        f'id={self.get_my_seat_id()}')
        print(response.json())

    # 退座
    def signback(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/signback?'
                                        f'id={self.get_my_seat_id()}')
        print(response.json())

    # 取消
    def cancel(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/cancel?'
                                        f'id={self.get_my_seat_id()}')
        print(response.json())

    # 时间戳转换1
    @classmethod
    def t_time(cls, timestamp):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(str(timestamp)[0:10])))
   
    # 时间戳转换2
    @classmethod
    def t_second(cls, timestamp):
        if timestamp:
            m, s = divmod(int(str(timestamp)[0:-3]), 60)
            h, m = divmod(m, 60)
            if m:
                if h:
                    return str(h) + "时" + str(m) + "分" + str(s) + "秒"
                return str(m) + "分" + str(s) + "秒"
            return str(s) + "秒"
        return "0秒"

    # 预约座位 需要自己修改
    def submit(self):
        # 获取token
        response = self.session.get(url='https://office.chaoxing.com/front/apps/seat/list?'
                                    f'deptIdEnc={self.deptIdEnc}')
        pageToken = re.compile(r"&pageToken=' \+ '(.*)' \+ '&").findall(response.text)[0]
        # print(pageToken)
        response = self.session.get(url='https://office.chaoxing.com/front/apps/seat/select?'
                                    'id=6296&'          # 房间id roomId 可以从self.room_id_name获取 请自行发挥
                                    'day=2022-03-01&'   # 预约时间 上下需保持一致
                                    'backLevel=2&'      # 必须的参数2
                                    f'pageToken={pageToken}')
        token = re.compile("token: '(.*)'").findall(response.text)[0]
        # print(token)
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/submit?'
                                    'roomId=6296&'      # 房间id roomId 上下需保持一致
                                    'startTime=9%3A00&' # 开始时间%3A代表: 自行替换9（小时）和后面00（分钟） 必须
                                    'endTime=11%3A00&'  # 结束时间 规则同上
                                    'day=2022-03-01&'   # 预约时间 上下需保持一致
                                    'seatNum=148&'      # 座位数字 与桌上贴纸一致
                                    f'token={token}')
        seat_result = response.json()
        print(seat_result)

    # 标准时间转换
    @classmethod
    def get_date(cls):
        return time.strftime('%a %b %d %Y %I:%M:%S GMT+0800 ', time.localtime(time.time())) + '(中国标准时间)'

    # 获取图书馆所有的房间和房间
    def get_all_room_and_seat(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/room/list?'
                                    f'deptIdEnc={self.deptIdEnc}')
        self.room = response.json()['data']['seatRoomList']
        self.deptId = self.room[0]['deptId']
        for index in self.room:
            self.room_id_capacity[index['id']] = index['capacity']
            self.db[index['id']] = 0
            self.room_id_name[index['id']] = index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName']
            response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/seatgrid/roomid?'
                                            'roomId={}'.format(index['id']))
            self.all_seat += response.json()['data']['seatDatas']
            # print(index['id'], index['capacity'], index['deptId'], index['firstLevelName'],
            #       index['secondLevelName'], index['thirdLevelName'])

    # 获取学习人数分布 多线程 2000座约10s
    def get_study_info(self):
        q = queue.Queue()
        for item in self.all_seat:
            q.put(item)
        ths = []
        for idx in range(0, 233):
            ths.append(
                threading.Thread(target=self.get_seat_info, args=(q,))
            )
        for th in ths:
            th.start()
        for th in ths:
            th.join()
        print('有人\t', '没人\t', '总共\t', '地点\t')
        for index in self.room:
            print(self.db[index['id']], ' ', '\t', self.room_id_capacity[index['id']] - self.db[index['id']], '\t',
                  self.room_id_capacity[index['id']], '\t', self.room_id_name[index['id']])
        print(self.db['sb'], '\t', self.db['nb'], '\t', len(self.all_seat))
        # 筛选座位 修改145可以看所有楼层的145座位信息 自行发挥
        # for index in self.all_seat:
        #     if index['seatNum'] == '145':
        #         print(index['seatNum'], index['id'], index['roomId'], self.room_id_name[index['roomId']])
        #     continue

    # 获取座位详细信息 配合get_study_info
    def get_seat_info(self, q: queue.Queue):
        while True:
            seat = q.get()
            response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/reserve/info?'
                                            'id={0}&seatNum={1}'.format(seat['roomId'], seat['seatNum'])).json()
            # print(response)
            try:
                r = response["data"]["seatReserve"]
                print(r["roomId"], r["seatNum"], r["id"], r["uid"],
                      self.t_time(r["startTime"]), self.t_time(r["endTime"]), self.room_id_name[r['roomId']])
                self.db[seat['roomId']] += 1
                self.db['sb'] += 1
            except:
                self.db['nb'] += 1
                # print(seat['roomId'], seat['seatNum'], '\t无人使用', self.room_id_name[seat['roomId']])
            if q.empty():
                break

    # 查询签到位置范围 没什么卵用 但是官方给了接口 那就安排上
    def get_sign_addr(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/address?'
                                    f'deptId={self.deptId}')
        for index in response.json()['data']['addressArr']:
            print(index['location'], index['offset'])

    # 获取到最近一次预约座位ID 默认的取消 签到 暂离都是默认这个 请自行发挥
    def get_my_seat_id(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/reservelist?'
                                        'indexId=0&'
                                        'pageSize=100&'
                                        'type=-1').json()['data']['reserveList']
        return response[0]['id']

    
