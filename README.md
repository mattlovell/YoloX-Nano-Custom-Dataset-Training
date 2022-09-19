<h2>YoloX-Nano Custom Dataset Training</h2>

Yolox-Nano Custom Dataset training, based on https://github.com/Megvii-BaseDetection/YOLOX/

<strong>Have adapted the EXP example file in the above repo to allow for training a YoloX-Nano model using VOC dataset to train on custom classes.</strong>

Use the above repo, and add this file to <strong>yolox_voc_nano.py</strong>  YOLOX/exps/example/yolox_voc/    


Use this line once training project configured:
<code>!python tools/train.py -f exps/example/yolox_voc/yolox_voc_nano.py -d 1 -b 8 --fp16 -o -c /content/YOLOX/yolox_nano.pth</code>

Tested on Google Colab Pro+

Total of 3200 images used to train 2 classes took approximately 5 hours and achieved best AP of 81.62 

map_5095: 0.8161757313333597
map_50: 0.9539941110554803



Final model can be deloyed for use on mobile for close to real time object detection after ONNX conversion


Colab Notebook to follow...
