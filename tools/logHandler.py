import logging
import os


# 创建自定义的 StreamHandler，用于控制台输出并设置不同级别的日志颜色
class ColoredStreamHandler(logging.StreamHandler):
    def emit(self, record):
        # 定义不同级别日志的颜色
        log_colors = {
            logging.DEBUG: "\033[0;37m",  # White
            logging.INFO: "\033[0;32m",  # Green
            logging.WARNING: "\033[0;33m",  # Yellow
            logging.ERROR: "\033[0;31m",  # Red
            logging.CRITICAL: "\033[0;35m",  # Magenta
        }

        try:
            message = self.format(record)
            self.stream.write(log_colors[record.levelno] + message + "\033[0m")  # Reset color
            self.stream.write(self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

class SingletonLogger:
    _instance = None

    def __new__(cls, logfilename="server.log", dir=""):
        if cls._instance is None:
            cls._instance = super(SingletonLogger, cls).__new__(cls)
            logfilename = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', logfilename))
            cls._instance.logger = cls._instance._create_logger(logfilename, dir)
        return cls._instance

    def _create_logger(self, logfilename, dir):
        # 创建日志记录器
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # 创建文件处理器
        log_dir = f'../logs/{dir}'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(log_dir, f'{logfilename}')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        #创建控制台处理器
        console_handler = ColoredStreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 将文件处理器和控制台处理器添加到日志记录器
        logger.addHandler(file_handler)
        # logger.addHandler(console_handler)

        return logger

if __name__ == '__main__':

    logger1 = SingletonLogger().logger
    logger2 = SingletonLogger().logger
    logger3 = SingletonLogger().logger

    logger1.info('这是一条日志信息')
    logger2.warning('这是一条警告信息')
    logger3.error('这是一条错误信息')
