import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# logging.getLogger('apscheduler').propagate = False
# logging.getLogger('telegram.vendor.ptb_urllib3').propagate = False

httpx_logger = logging.getLogger('httpx')
httpx_logger.setLevel(logging.WARNING)


# Crear un filtro personalizado
class InfoWarningFilter(logging.Filter):
    def filter(self, record):
        return record.levelno <= logging.WARNING


# Crear un manejador para stdout (nivel INFO y WARNING)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
stdout_handler.addFilter(InfoWarningFilter())

# Crear un manejador para stderr (nivel ERROR)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.ERROR)
stderr_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))

# Agregar los manejadores al registro
logger = logging.getLogger()
logger.addHandler(stdout_handler)
logger.addHandler(stderr_handler)

# Ejemplos de registros
logger.info("Este es un mensaje de nivel INFO (stdout)")
logger.warning("Este es un mensaje de nivel WARNING (stdout)")
logger.error("Este es un mensaje de nivel ERROR (stderr)")
