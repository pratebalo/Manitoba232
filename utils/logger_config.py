import logging

# Configura el sistema de registro
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s: %(message)s')

httpx_logger = logging.getLogger('httpx')
httpx_logger.setLevel(logging.WARNING)
# logging.getLogger('apscheduler').propagate = False
# logging.getLogger('telegram.vendor.ptb_urllib3').propagate = False


# Crea dos manejadores de registro diferentes
info_warning_handler = logging.FileHandler('info_warning.log')
error_handler = logging.FileHandler('error.log')


# Crea un filtro personalizado para INFO y WARNING
class InfoWarningFilter(logging.Filter):
    def filter(self, record):
        return record.levelno <= logging.WARNING


# Aplica el filtro personalizado al manejador de info_warning
info_warning_handler.addFilter(InfoWarningFilter())

# Configura el nivel de registro para cada manejador
info_warning_handler.setLevel(logging.INFO)
error_handler.setLevel(logging.ERROR)

# Configura el formato de registro para los manejadores
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
info_warning_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)

# Crea un registro
logger = logging.getLogger()

# Agrega los manejadores al registro
logger.addHandler(info_warning_handler)
logger.addHandler(error_handler)

# Ejemplos de registros
logger.info("Este es un mensaje de nivel INFO (info_warning.log)")
logger.warning("Este es un mensaje de nivel WARNING (info_warning.log)")
logger.error("Este es un mensaje de nivel ERROR (error.log)")
