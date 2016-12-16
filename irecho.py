#!/usr/bin/env python
# coding=utf-8

'''
学習リモコン化したArduinoをシリアル通信で制御するプログラム

使用非標準ライブラリ
PySerial ( pip install pyserial )
'''

import argparse
import serial
import time
import sqlite3
import re
import os

ser = serial.Serial()
default_database = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'data.sqlite')
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--database', default=default_database,
        help='データベース名')
    subs = parser.add_subparsers(dest='subcommand')

    sub_recv = subs.add_parser('recv', help='赤外線信号を受信する')
    sub_recv.add_argument(
        '--name', metavar='NAME', type=signal_name_type,
        help='信号の保存名')
    sub_recv.add_argument(
        '--serial-port', metavar='PORT', required=True, help='シリアルポート')
    sub_recv.set_defaults(cmd=cmd_recv)

    sub_send = subs.add_parser('send', help='赤外線信号を送信する')
    sub_send.add_argument(
        '--name', metavar='NAME', required=True, type=signal_name_type,
        help='送信する信号名')
    sub_send.add_argument(
        '--serial-port', metavar='PORT', required=True, help='シリアルポート')
    sub_send.set_defaults(cmd=cmd_send)

    sub_list = subs.add_parser('list', help='保存した赤外線信号を一覧表示する')
    sub_list.set_defaults(cmd=cmd_list)

    sub_del = subs.add_parser('del', help='保存した赤外線信号を削除する')
    sub_del.add_argument(
        '--name', metavar='NAME', required=True, type=signal_name_type,
        help='削除する信号名')
    sub_del.set_defaults(cmd=cmd_del)

    args = parser.parse_args()
    if args.subcommand:
        args.cmd(args)
    else:
        parser.print_help()


def signal_name_type(name):
    if re.match(r'[a-zA-Z][a-zA-Z0-9\-_]{0,31}', name):
        return name
    else:
        raise argparse.ArgumentTypeError(
            'signal name must be "[a-zA-Z][a-zA-Z0-9\-_]{0,31}".'
        )


def get_db_connection(database):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS signals (name TEXT PRIMARY KEY, data TEXT)
    """)
    return conn


def save_signal(conn, name, data):
    conn.cursor().execute("""
    INSERT OR REPLACE INTO signals VALUES (?, ?)
    """, (name, ', '.join(map(str, data))))


def get_signal(conn, name):
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM signals WHERE name = ?
    """, (name, ))
    return cur.fetchone()


def delete_signal(conn, name):
    cur = conn.cursor()
    cur.execute("""
    DELETE FROM signals WHERE name = ?
    """, (name, ))
    return cur.rowcount


def list_signals(conn):
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM signals ORDER BY name
    """)
    return cur.fetchall()


def cmd_recv(args):
    serial_open(args)
    data = do_recv()
    if data and args.name:
        conn = get_db_connection(args.database)
        save_signal(conn, args.name, data)
        conn.commit()
        conn.close()
        print('signal({}) saved.'.format(args.name))


def cmd_send(args):
    conn = get_db_connection(args.database)
    signal = get_signal(conn, args.name)
    if signal:
        serial_open(args)
        do_send(
            [int(d) for d in signal[1].split(',') if d]
        )
    else:
        print('signal({}) not found.'.format(args.name))


def cmd_list(args):
    conn = get_db_connection(args.database)
    for r in list_signals(conn):
        print(r)


def cmd_del(args):
    conn = get_db_connection(args.database)
    if delete_signal(conn, args.name):
        conn.commit()
        conn.close()
        print('signal({}) deleted.'.format(args.name))
    else:
        print('signal({}) not found.'.format(args.name))


def serial_open(args):
    # シリアル通信をオープン（openの前にsetDTRしないと毎回arduinoがリセットされて待ち時間が発生する）
    ser.port = args.serial_port
    ser.baudrate = 9600
    ser.setDTR(False)
    ser.open()


def is_idle():
    ser.write(b'I')
    return ser.readline().startswith(b'IDLE')


def when_idle(func):
    def inner(*args):
        if is_idle():
            return func(*args)
    return inner


@when_idle
def do_recv():
    data = []
    ser.write(b'R')
    while True:
        line = ser.readline()
        print(line)
        if line.startswith(b'DATA'):
            data = [int(d) for d in line.strip().split(b',')[1:] if d]
        elif line.startswith(b'DONE'):
            break
    return data


@when_idle
def do_send(data):
    datastr = b','.join(map(lambda x: bytes(str(x), 'ascii'), data)) + b'\n'
    chunks = [datastr[i:i+63] for i in range(0, len(datastr), 63)]
    recognized = []
    ser.write(b'S')
    while True:
        line = ser.readline()
        print(line)
        if line.startswith(b'SEND') or line.startswith(b'THEN'):
            if len(chunks):
                print('chunk write {}'.format(len(chunks)))
                ser.write(chunks.pop(0) + b'C')
                ser.flush()
        elif line.startswith(b'DATA'):
            recognized = [int(d) for d in line.strip().split(b',')[1:] if d]
        elif line.startswith(b'DONE'):
            break
    return recognized

if __name__ == '__main__':
    main()
