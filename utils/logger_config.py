import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger('apscheduler').propagate = False
logging.getLogger('telegram.vendor.ptb_urllib3').propagate = False


warning_log_handler = logging.FileHandler('normal.log')
warning_log_handler.setLevel(logging.WARNING)  # Este manejará registros de advertencia
warning_log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
warning_log_handler.setFormatter(warning_log_format)

error_log_handler = logging.FileHandler('errors.log')
error_log_handler.setLevel(logging.ERROR)  # Este solo manejará registros de error
error_log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_log_handler.setFormatter(error_log_format)

logger.addHandler(error_log_handler)
logger.addHandler(warning_log_handler)
