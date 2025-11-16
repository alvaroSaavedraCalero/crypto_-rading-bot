# data/downloader.py

from pathlib import Path

import ccxt
import pandas as pd


# Directorio de datos (carpeta /data en la raíz del proyecto)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def get_binance_exchange() -> ccxt.binance:
    """
    Crea una instancia de Binance usando ccxt para datos públicos (sin API key).
    enableRateLimit: respeta límites de peticiones.
    """
    exchange = ccxt.binance({
        "enableRateLimit": True,
        "options": {
            "adjustForTimeDifference": True,
        },
    })
    return exchange


def _timeframe_to_ms(timeframe: str) -> int:
    """
    Convierte un timeframe tipo '15m', '1h', '4h', '1d' a milisegundos aproximados.
    """
    unit = timeframe[-1]
    value = int(timeframe[:-1])

    if unit == "m":
        return value * 60 * 1000
    elif unit == "h":
        return value * 60 * 60 * 1000
    elif unit == "d":
        return value * 24 * 60 * 60 * 1000
    else:
        raise ValueError(f"Timeframe no soportado: {timeframe}")


def fetch_datos_cripto(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    limit: int = 1000,
) -> pd.DataFrame:
    """
    Descarga datos OHLCV desde Binance.

    Si limit <= 1000: una sola llamada.
    Si limit  > 1000: varias llamadas paginadas hasta cubrir ese número aproximado de velas.
    """
    exchange = get_binance_exchange()

    # Caso sencillo: máximo 1000 velas
    if limit <= 1000:
        raw_ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    else:
        all_ohlcv = []
        tf_ms = _timeframe_to_ms(timeframe)

        # Estimamos un 'since' inicial suficientemente atrás en el tiempo
        now_ms = exchange.milliseconds()
        since_ms = now_ms - limit * tf_ms

        while len(all_ohlcv) < limit:
            remaining = limit - len(all_ohlcv)
            this_limit = min(1000, remaining)

            chunk = exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=since_ms,
                limit=this_limit,
            )

            if not chunk:
                break

            all_ohlcv.extend(chunk)

            # Avanzamos 'since' al final del último chunk para evitar duplicados
            last_ts = chunk[-1][0]
            since_ms = last_ts + tf_ms

            # Seguridad: si el último timestamp no avanza, rompemos
            if len(chunk) < this_limit:
                break

        raw_ohlcv = all_ohlcv

    if not raw_ohlcv:
        raise ValueError(
            f"No se han descargado datos para {symbol} en {timeframe}. "
            f"Comprueba el símbolo y la red."
        )

    df = pd.DataFrame(
        raw_ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )

    # Convertir timestamp de ms a datetime UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    # Eliminar posibles duplicados y ordenar por tiempo
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)

    # Si hemos traído más de 'limit' velas por seguridad, nos quedamos con las últimas 'limit'
    if len(df) > limit:
        df = df.tail(limit).reset_index(drop=True)

    # Validaciones básicas
    if df.empty:
        raise ValueError("El DataFrame de datos descargados está vacío.")

    if df[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise ValueError("Se han encontrado NaNs en los datos descargados.")

    return df



def build_csv_path(symbol: str, timeframe: str) -> Path:
    """
    Construye una ruta de archivo CSV consistente para un símbolo y timeframe.
    Ejemplo: BTCUSDT_1h.csv
    """
    # Evitar '/' en el nombre del archivo
    clean_symbol = symbol.replace("/", "")
    filename = f"{clean_symbol}_{timeframe}.csv"
    return DATA_DIR / filename


def save_datos_cripto_to_csv(
    df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
) -> Path:
    """
    Guarda un DataFrame OHLCV en un archivo CSV dentro de /data.

    Devuelve la ruta del archivo guardado.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)  # Asegura que /data existe
    csv_path = build_csv_path(symbol, timeframe)

    # Guardamos en CSV sin índice
    df.to_csv(csv_path, index=False)

    return csv_path


def load_datos_cripto_from_csv(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
) -> pd.DataFrame:
    """
    Carga datos OHLCV desde un CSV previamente guardado.

    Realiza validaciones básicas:
    - Existe el archivo
    - No está vacío
    - Timestamps correctos y ordenados
    - Sin duplicados
    """
    csv_path = build_csv_path(symbol, timeframe)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"No se ha encontrado el archivo de datos: {csv_path}. "
            f"Primero descarga los datos con fetch_datos_cripto() y save_datos_cripto_to_csv()."
        )

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError(f"El archivo {csv_path} está vacío.")

    # Asegurarse de que la columna timestamp es datetime UTC
    if "timestamp" not in df.columns:
        raise ValueError(f"El archivo {csv_path} no tiene columna 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Eliminar duplicados y ordenar
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)

    # Validación de NaNs
    if df[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise ValueError(f"Se han encontrado NaNs en los datos cargados desde {csv_path}.")

    return df


def fetch_and_save_datos_cripto(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    limit: int = 1000,
) -> pd.DataFrame:
    """
    Función de conveniencia: descarga datos y los guarda directamente en CSV.
    Devuelve el DataFrame descargado.
    """
    df = fetch_datos_cripto(symbol=symbol, timeframe=timeframe, limit=limit)
    csv_path = save_datos_cripto_to_csv(df, symbol=symbol, timeframe=timeframe)
    print(f"Guardados {len(df)} registros en {csv_path}")
    return df


def get_datos_cripto_cached(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    limit: int = 1000,
    force_download: bool = False,
) -> pd.DataFrame:
    """
    Obtiene datos OHLCV usando un CSV como caché.

    - Si existe el CSV y no se fuerza descarga -> carga desde CSV.
    - Si no existe el CSV o force_download=True -> descarga de Binance y guarda CSV.

    El parámetro 'limit' se respeta al:
    - Descargar: se pasa directamente a Binance.
    - Cargar desde CSV: se devuelven las últimas 'limit' velas, si hay más.
    """
    csv_path = build_csv_path(symbol, timeframe)

    if csv_path.exists() and not force_download:
        # Cargar desde CSV
        df = load_datos_cripto_from_csv(symbol=symbol, timeframe=timeframe)
        if limit is not None and len(df) > limit:
            df = df.tail(limit).reset_index(drop=True)
        print(f"Usando datos locales desde {csv_path} ({len(df)} velas).")
        return df

    # Descargar de Binance y guardar
    df = fetch_datos_cripto(symbol=symbol, timeframe=timeframe, limit=limit)
    csv_path = save_datos_cripto_to_csv(df, symbol=symbol, timeframe=timeframe)
    print(f"Descargados y guardados {len(df)} registros en {csv_path}.")
    return df
