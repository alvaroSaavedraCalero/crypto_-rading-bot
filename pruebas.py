
import data.downloader as d
print("Módulo:", d)
print("Atributos que contienen 'fetch':")
print([name for name in dir(d) if "fetch" in name])