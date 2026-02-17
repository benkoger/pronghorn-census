# Methods for presenting images to users
# Authors: Ben Koger, Michael B. Lance
# Created: February 26, 2025
# Updated: May 9, 2025

#---------------------------------------------------------------------------------------------------------------------------#
from abc import ABC, abstractmethod 
from ..generatorobjects.generatorobjects import Image, ReviewedArea, Prediction, Box, PredictionCrop
import os
import numpy as np
import math
from typing import Dict, List, Union
import cv2

#---------------------------------------------------------------------------------------------------------------------------#

class ImageBackend(ABC):
    
    @abstractmethod
    async def evaluate_crop(self, crop: ReviewedArea, predictions: list[Prediction], class_name, drawBox:bool=False):
        pass
    

#---------------------------------------------------------------------------------------------------------------------------#

def evaluate_crops(self, crops: Dict[str, Union[ReviewedArea, List[Prediction]]], label:str):
    approved_crops = []
    for crop_num in crops.keys():
        crop = crops[crop_num]['crop']
        predictions = crops[crop_num]['predictions']
        resp = self.evaluate_crop(crop, predictions, label)
        if resp:
            approved_crops.append(crop)
    return approved_crops
    
#---------------------------------------------------------------------------------------------------------------------------#

class MatplotBackend(ImageBackend):
    import matplotlib.pyplot as plt

    def prompt_user(self, class_name): 
        if os.name == 'posix':
            pass
            os.system('clear')
        else:
            os.system('cls')

        while True: # Show number associated with crop indexes in plot
            user_input = input(f'Please indicate (yes or no) whether any displayed image is of a {class_name}, q to quit: \n')
            try:
                if user_input in set(['q', 'Q', 'Quit', 'quit', 'QUIT']):
                    print('Quitting...')
                    return -999 

                if user_input in set(['y', 'Y', 'yes', 'Yes', '1']):
                    return True
                elif user_input in set(['n', 'N', 'no', 'No', '0']):
                    return False
                
            except:
                continue 

    def evaluate_crop(crops: list[PredictionCrop], class_name, drawBox:bool=False):
        img = image.getImage()
        scale_factor = 2
        crop_size = 2
        max_cols = 6
        max_crops = 36
        
        crops = crops[:max_crops] #type: ignore
        if len(crops) <= max_cols:
            cols = len(crops)
            rows = 1
        else:
            cols = max_cols
            rows = math.ceil(len(crops) / max_cols)

        fig, axs = self.plt.subplots(rows, cols, figsize=(cols * crop_size * scale_factor, rows * crop_size * scale_factor))


        # axs = [axs]
        for ax, crop, pred in zip(fig.axes[:len(crops)], crops, predictions):
            ax.imshow(crop)
            ax.set_title(f'score: {pred.score:.3f}')
            ax.set_axis_off() 
    
        self.plt.figure(figsize=(15,15))
        self.plt.imshow(img)
        self.plt.axis('off')
        self.plt.close() 
        self.plt.show(block=False)
        out = self.prompt_user(class_name)
        self.plt.close(fig)
        if out == -999:
            return -999
        return out #type: ignore
    
#---------------------------------------------------------------------------------------------------------------------------#

class OpencvBackend(ImageBackend):

    def prompt_user(self, key):
        if key == ord('q'):
                cv2.destroyAllWindows()
                return -999
            
        if key in set([ord('y'), ord('Y'), ord('1')]):
            return True
        if key in set([ord('n'), ord('N'), ord('0')]):
            return False

    async def evaluate_crop(self, image: ReviewedArea, predictions: list[Prediction], desired_class: int, class_name, drawBox:bool=False):
        crops = self.create_subcrop(image, predictions, desired_class, drawBox)
        
        if os.name == 'posix':
            pass
            os.system('clear')
        else:
            os.system('cls')

        for crop, score in zip(crops, prediction['scores']): #type: ignore
            cv2.imshow(f'score: {score}', cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            
            key = cv2.waitKey(0)
            
            out = self.prompt_user(key)
            cv2.destroyAllWindows()

            if out == -999:
                return -999
            return out

#---------------------------------------------------------------------------------------------------------------------------#

def get_backend(backend_type: str):
    backends = {
    'matplot': MatplotBackend,
    'opencv': OpencvBackend,
    }

    return backends[backend_type]