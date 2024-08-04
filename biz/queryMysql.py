import json
import os

import pymysql

from tools.logHandler import SingletonLogger

logging = SingletonLogger().logger


def connectMysqlQuery(host, port, user, passwd, database, sql):
    # 连接到数据库
    connection = pymysql.connect(host=host,
                                 port=port,
                                 user=user,
                                 password=passwd,
                                 database=database)

    try:
        with connection.cursor() as cursor:
            # 执行查询SQL语句
            cursor.execute(sql)
            connection.commit()

            # 获取查询结果
            return cursor.fetchall()
    finally:
        # 关闭数据库连接
        connection.close()


def queryMysql(dbName, sql):
    # 读取配置文件, 处理mock
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'mysql.config'))
    with open(config_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    config = data[f'{dbName}']
    result = connectMysqlQuery(config['host'], config['port'], config['user'], config['passwd'], config['database'],
                               sql)
    logging.info(f"mysql query result: {result}")
    return result


if __name__ == '__main__':
    r = queryMysql('zd_uat', "select * from ddx where id = '1769850004763062272111';")
    print(r[0])
