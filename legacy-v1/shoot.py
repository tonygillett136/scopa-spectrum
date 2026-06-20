import sys
sys.path.insert(0,"/Volumes/SSD1/code/retro_computing/zxspectrum/mastery/tools")
from zx_shot import Speccy
with Speccy(port=10000) as zx:
    zx.smartload("/Volumes/SSD1/code/retro_computing/zxspectrum/scopa/harness_proto.sna")
    zx.sleep(1.0); zx.screenshot("/tmp/scopa_proto.png")
    print("shot saved", flush=True)
