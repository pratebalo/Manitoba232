import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
# logging.getLogger('apscheduler').propagate = False
# logging.getLogger('telegram.vendor.ptb_urllib3').propagate = False

httpx_logger = logging.getLogger('httpx')
httpx_logger.setLevel(logging.WARNING)
