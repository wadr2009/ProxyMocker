# 功能概述
常规mock工具一般通过修改调用的域名/调用地址等形式实现mock功能. 无法满足以下几点需求:
1. 第三方服务有多个接口, 只想mock其中一部分
2. 只mock特定请求, 其他请求正常走业务处理
3. 第三方处理请求后, 再进行mock响应
4. 微服务部署在k8s, 通过Fegin进行模块间调用时, 想要mock接口成本较高

此项目为解决以上问题而产生, 且可以通过调用其他mock平台扩充自身能力边界 
# 整体流程
![image](https://github.com/user-attachments/assets/03f10030-56f8-4dce-9e7c-79ee4181f45e)

# 部署
通过docker部署, 运行Dockerfile启动容器
# 功能场景
1. 请求被mock服务后修改响应
```
{
"/api/test0": { //需要mock的接口url
        "mockApiName": "发送给实际请求服务后, 替换响应", //需要mock的接口名称
        "mockCheck": "2",  //判断是否需要mock 请求或响应包含此字符串即通过check
        //直接修改响应
        "returnBody": "{\"code\":\"0000\",\"data\":{\"fileBase64Str\":\"${convert_to_base64(000.csv)}\"},\"msg\":\"成功\"}"
    }
}
```
3. 直接mock接口
```
{
    "/api/xml": {
        "isXmlApi": true, //是否为xml接口
        "mockApiName": "xml接口示例",
        "mockCheck": "1",
        "mockRequest": {
            "redirection": "http://localhost:5001/api/xml" //内置挡板
        },
        "returnBody": "默认返回", 
        "otherReturnBody": { //其他返回规则
            "$.data.transcode=001": "返回内容1",
            "$.data.transcode=002": "返回内容2"
}
```
4. 将请求转发给第三方mock平台后修改返回
```
{
"/api/test1": {
        "mockApiName": "转发给其他mock平台处理示例-转发",
        "mockCheck": "Your check parameters",
        "mockRequest": {
            "redirection": "https://mock.com/mock/api/test1",
            "toGet": true //转发为get请求
        },
        "returnBody": "",
        "timeout": 0 //设置接口超时
    },
    "/mock/api/test1": {
        "mockApiName": "转发给其他mock平台处理示例-返回后再次修改",
        "mockCheck": "Your check parameters", //判断是否需要mock 请求或响应包含此字符串即通过check
        "byDbReplace": {//通过查询数据库的内容修改响应
            "check": "xxxxxx", //判断是否执行, 规则同mockCheck字段
            "dbname": "db1", //数据库名称(在数据库配置中)
            "rule": { //替换规则
                "data.amountTax": -1, //响应jsonpath, 数据返回值的索引
                "data.name": 1,
                "data.totalAmount": 2
            },
            //查询sql
            "sql": "select id, name, totalAmount, amountTax from table i where i.number = '{number}';",
            "sqlParam": {//sql使用的参数 请求jsonpath
                "number": "data.number"
            }
        },
        "byResReplace": {//直接替换响应
            "check": "xxxxxx", //判断是否替换
            "rule": {//替换规则
                "data.state": 0 ////响应jsonpath, 替换结果
            }
        }
    }
}
```

# 可调用接口
查询配置
- GET /mock/get_config
保存配置
- POST  /mock/save_config
传入配置的json内容
获取配置
- GET /mock/get_config
获取日志
- GET /streamMockLog?lines=需要的最新日志行数

# 可变参数和hook
注: 仅配置在接口返回中可用
变量
- 从原始请求(request)或响应(response)中提取, 规则为jsonpath 如 $.request.data.code  (提取请求参数中的data.code)
方法
- ${convert_to_base64(1.csv)} ,执行convert_to_base64方法, 参数为1.csv
- ${getResult($request_cipher)}} ,执行getResult方法,参数为$request_cipher(会先提取变量)
- 支持python内置方法

# 项目接入
http请求工具底层需使用HttpsURLConnection类, 且默认支持http代理
