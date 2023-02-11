# CMNeRF



--------------------------------------

### Prerequisites

- Note: for Azure ML support for this repository, please consider checking out [this branch](https://github.com/szymanowiczs/bundle-adjusting-NeRF/tree/azureml_training_script) by Stan Szymanowicz.

This code is developed with Python3 (`python3`). PyTorch 1.9+ is required.  
It is recommended use [Anaconda](https://www.anaconda.com/products/individual) to set up the environment. Install the dependencies and activate the environment `barf-env` with
```bash
conda env create --file requirements.yaml python=3
conda activate barf-env
```
Initialize the external submodule dependencies with
```bash
git submodule update --init --recursive
```

--------------------------------------

### Data

- #### Synthetic data (Blender) and real-world data (LLFF)
    Both the Blender synthetic data and LLFF real-world data can be found in the [NeRF Google Drive](https://drive.google.com/drive/folders/128yBriW1IG_3NJ5Rp7APSTZsJqdJdfc1).
For convenience, you can download them with the following script: (under this repo)
  ```bash
  # Blender
  gdown --id 18JxhpWD-4ZmuFKLzKlAw-w5PpzZxXOcG # download nerf_synthetic.zip
  unzip nerf_synthetic.zip
  rm -f nerf_synthetic.zip
  mv nerf_synthetic data/blender
  # LLFF
  gdown --id 16VnMcF1KJYxN9QId6TClMsZRahHNMW5g # download nerf_llff_data.zip
  unzip nerf_llff_data.zip
  rm -f nerf_llff_data.zip
  mv nerf_llff_data data/llff
  ```
  The `data` directory should contain the subdirectories `blender` and `llff`.
  If you already have the datasets downloaded, you can alternatively soft-link them within the `data` directory.

- #### <span style="color:red">Test your own sequence!</span>
  If you want to try BARF on your own sequence, we provide a template data file in `data/iphone.py`, which is an example to read from a sequence captured by an iPhone 12.
  You should modify `get_image()` to read each image sample and set the raw image sizes (`self.raw_H`, `self.raw_W`) and focal length (`self.focal`) according to your camera specs.  
  You may ignore the camera poses as they are assumed unknown in this case, which we simply set to zero vectors.


- #### <span style="color:red">Strayscanner</span>
    Both the Bl  (strayscanner)[https://docs.strayrobots.io/]
  If you want to try BARF on your own sequence, we provide a template data file in `data/iphone.py`, which is an example to read from a sequence captured by an iPhone 12.
  You should modify `get_image()` to read each image sample and set the raw image sizes (`self.raw_H`, `self.raw_W`) and focal length (`self.focal`) according to your camera specs.  
  You may ignore the camera poses as they are assumed unknown in this case, which we simply set to zero vectors.


#### BARF DATA
- ios_logger frame [right,up,backward]
- BARF 각 데이터.py 하단에 parse_raw_camera() 거치면 [right,down,forward]로 바꿈. 

- strayscanner frame [right,down,forward] 라서 변환 필요 없음.

(인풋 데이터 프레임은 [right,up,backward]로 받아서 내부에서 [right, up, backwards]로 전환 후 사용함)
BARF의 the coordinate system of this function output would be [right, up, backwards]
![KakaoTalk_20220406_111550975](https://user-images.githubusercontent.com/35680342/161882313-513b9abc-22f8-4c8b-a300-c8959cccff91.jpg)
![image](https://user-images.githubusercontent.com/35680342/195963443-62e8de25-dfbc-4905-9e51-0be3f33c3ea8.png)




--------------------------------------

If you find our code useful for your research, please cite
```
@inproceedings{lin2021barf,
  title={BARF: Bundle-Adjusting Neural Radiance Fields},
  author={Lin, Chen-Hsuan and Ma, Wei-Chiu and Torralba, Antonio and Lucey, Simon},
  booktitle={IEEE International Conference on Computer Vision ({ICCV})},
  year={2021}
}

@inproceedings{roessle2022dense,
  title={Dense depth priors for neural radiance fields from sparse input views},
  author={Roessle, Barbara and Barron, Jonathan T and Mildenhall, Ben and Srinivasan, Pratul P and Nie{\ss}ner, Matthias},
  booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition},
  pages={12892--12901},
  year={2022}
}

MINE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

```

### Acknowledgements
This code borrows heavily from [BARF](https://github.com/chenhsuanlin/bundle-adjusting-NeRF).
We thank [BARF](https://github.com/chenhsuanlin/bundle-adjusting-NeRF), from which this repository borrows code. 


Please contact me (yunjingong731@gmail.com) if you have any questions!
