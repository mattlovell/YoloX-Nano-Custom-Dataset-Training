# encoding: utf-8
import os
import random
import torch
import torch.nn as nn
import torch.distributed as dist

from yolox.exp import Exp as MyExp
from yolox.data import get_yolox_datadir

# edit value in lines 75, 125,126
# e.g. VOCdevkit
# and set to folder name of VOC dateset being used
# e.g. 2007
# 
# this example uses the YoloX-Nano weights
# found here:https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.pth



class Exp(MyExp):
    def __init__(self):
        super(Exp, self).__init__()
        self.num_classes = 2 #you may want to change this accordingly!
        self.depth = 0.33
        self.width = 0.25
        self.input_size = (416, 416)
        self.random_size = (10, 20)
        self.mosaic_scale = (0.5, 1.5)
        self.test_size = (416, 416)
        self.mosaic_prob = 0.5
        self.enable_mixup = False
        self.exp_name = os.path.split(os.path.realpath(__file__))[
            1].split(".")[0]

        # --------------  training config --------------------- #
        self.warmup_epochs = 1
        self.max_epoch = 300
        self.warmup_lr = 0
        self.basic_lr_per_img = 0.01 / 64.0
        self.scheduler = "yoloxwarmcos"
        self.no_aug_epochs = 15
        self.min_lr_ratio = 0.04
        self.ema = True

        self.weight_decay = 5e-4
        self.momentum = 0.9

    def get_model(self, sublinear=False):

        def init_yolo(M):
            for m in M.modules():
                if isinstance(m, nn.BatchNorm2d):
                    m.eps = 1e-3
                    m.momentum = 0.03
        if "model" not in self.__dict__:
            from yolox.models import YOLOX, YOLOPAFPN, YOLOXHead
            in_channels = [256, 512, 1024]
            # NANO model use depthwise = True, which is main difference.
            backbone = YOLOPAFPN(self.depth, self.width,
                                 in_channels=in_channels, depthwise=True)
            head = YOLOXHead(self.num_classes, self.width,
                             in_channels=in_channels, depthwise=True)
            self.model = YOLOX(backbone, head)

        self.model.apply(init_yolo)
        self.model.head.initialize_biases(1e-2)
        return self.model

    def get_data_loader(self, batch_size, is_distributed, no_aug=False):
        from yolox.data import (
            VOCDetection,
            TrainTransform,
            YoloBatchSampler,
            DataLoader,
            InfiniteSampler,
            MosaicDetection,
        )

        dataset = VOCDetection(
            data_dir=os.path.join(get_yolox_datadir(), "VOCdevkit"),
            image_sets=[('2007', 'trainval')],
            img_size=self.input_size,
            preproc=TrainTransform(
                rgb_means=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
                max_labels=3,
            ),
        )

        dataset = MosaicDetection(
            dataset,
            mosaic=no_aug,  # not
            img_size=self.input_size,
            preproc=TrainTransform(
                rgb_means=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
                max_labels=3,
            ),
            degrees=self.degrees,
            translate=self.translate,
            scale=self.scale,
            shear=self.shear,
            perspective=self.perspective,
            enable_mixup=self.enable_mixup,
        )

        self.dataset = dataset

        if is_distributed:
            batch_size = batch_size // dist.get_world_size()

        sampler = InfiniteSampler(
            len(self.dataset), seed=self.seed if self.seed else 0
        )

        batch_sampler = YoloBatchSampler(
            sampler=sampler,
            batch_size=batch_size,
            drop_last=False,
            input_dimension=self.input_size,
            mosaic=not no_aug,
        )

        dataloader_kwargs = {
            "num_workers": self.data_num_workers, "pin_memory": True}
        dataloader_kwargs["batch_sampler"] = batch_sampler
        train_loader = DataLoader(self.dataset, **dataloader_kwargs)

        return train_loader

    def get_eval_loader(self, batch_size, is_distributed, testdev=False):
        from yolox.data import VOCDetection, ValTransform

        valdataset = VOCDetection(
            data_dir=os.path.join(get_yolox_datadir(), "VOCdevkit"),
            image_sets=[('2007', 'test')],
            img_size=self.test_size,
            preproc=ValTransform(
                rgb_means=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        )

        if is_distributed:
            batch_size = batch_size // dist.get_world_size()
            sampler = torch.utils.data.distributed.DistributedSampler(
                valdataset, shuffle=False
            )
        else:
            sampler = torch.utils.data.SequentialSampler(valdataset)

        dataloader_kwargs = {
            "num_workers": self.data_num_workers,
            "pin_memory": True,
            "sampler": sampler,
        }
        dataloader_kwargs["batch_size"] = batch_size
        val_loader = torch.utils.data.DataLoader(
            valdataset, **dataloader_kwargs)

        return val_loader

    def get_evaluator(self, batch_size, is_distributed, testdev=False):
        from yolox.evaluators import VOCEvaluator

        val_loader = self.get_eval_loader(
            batch_size, is_distributed, testdev=testdev)
        evaluator = VOCEvaluator(
            dataloader=val_loader,
            img_size=self.test_size,
            confthre=self.test_conf,
            nmsthre=self.nmsthre,
            num_classes=self.num_classes,
        )
        return evaluator
