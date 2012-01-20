from distutils.core import setup 
import py2exe 
#setup(console=["main.py"])

setup(
    options = {
      "py2exe": {
        "dll_excludes": ["MSVCP90.dll"],
      }
    },
    windows=[{"script": "main.py"}]
)
