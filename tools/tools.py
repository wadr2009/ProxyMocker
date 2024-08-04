
#sql组装
def sqlHandle(sql, result, sqlParamConfig):
    sqlParam = {}
    for key, value in sqlParamConfig.items():
        key_parts = value.split('.')
        current_data = result
        for part in key_parts[:-1]:
            current_data = current_data.get(part, {})
        sqlParam[key] = current_data[key_parts[-1]]

    # 使用格式化字符串替换参数
    return sql.format(**sqlParam)
