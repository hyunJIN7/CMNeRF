# CMNeRF



--------------------------------------

### Setup

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
  Place your scene directory somewhere. Follow the Strayscanner data structure.
  If you want to try CMNeRF on your own sequence, we provide a template data file in `data/strayscanner.py`, which is an example to read from a sequence captured by an iPhone 12 pro.   You should modify `get_image()` to read each image sample and set the raw image sizes (`self.raw_H`, `self.raw_W`) and focal length (`self.focal`) and (`self.pose`) w2c pose([right,down,forward]) and depth information (`self.gt_depth`, `self.confidence`)  according to your camera specs.  
Note: if you use this data format, make sure your `dataset_type` in the config file is set as `strayscanner`.


- #### <span style="color:red">Strayscanner</span>
    Acquire data using (Strayscanner)[https://docs.strayrobots.io/].
  
To generate the train/test data:
```
python data/process_strayscanner_data_image_resize.py --basedir <your_scenedir>
python data/process_strayscanner_data_image_resize.py --basedir ./data/strayscanner/chair 
```

--------------------------------------


### Running the code

- #### BARF models
  To train and evaluate BARF:
  ```bash
  # <GROUP> and <NAME> can be set to your likes, while <SCENE> is specific to datasets
  
  # Blender (<SCENE>={chair,drums,ficus,hotdog,lego,materials,mic,ship})
  python3 train.py --group=<GROUP> --model=barf --yaml=barf_blender --name=<NAME> --data.scene=<SCENE> --barf_c2f=[0.1,0.5]
  python3 evaluate.py --group=<GROUP> --model=barf --yaml=barf_blender --name=<NAME> --data.scene=<SCENE> --data.val_sub= --resume
  python3 train.py --group=blender --model=barf --yaml=barf_blender --name=result_lego --data.scene=lego --barf_c2f=[0.1,0.5]
  python3 evaluate.py --group=blender --model=barf --yaml=barf_blender --name=result_lego --data.scene=lego --data.val_sub= --resume
  
  # LLFF (<SCENE>={fern,flower,fortress,horns,leaves,orchids,room,trex})
  python3 train.py --group=<GROUP> --model=barf --yaml=barf_llff --name=<NAME> --data.scene=<SCENE> --barf_c2f=[0.1,0.5]
  python3 evaluate.py --group=<GROUP> --model=barf --yaml=barf_llff --name=<NAME> --data.scene=<SCENE> --resume
  
    #strayscanner
  python3 train.py --group=strayscanner --model=barf --yaml=barf_strayscanner --name=result_chair --data.scene=chair  --barf_c2f=[0.1,0.5] --depth.use_depth=true --depth.use_depth_loss=true 
  python3 evaluate.py --group=strayscanner --model=barf --yaml=barf_strayscanner --name=result_chair --data.scene=chair  --data.val_sub= --depth.use_depth=true --depth.use_depth_loss=true 
  
  #iphone (If you want to train the reference BARF models)
  python3 train.py --group=iphone --model=barf --yaml=barf_iphone --name=result_chair --data.scene=chair  --barf_c2f=[0.1,0.5]  --depth.use_depth=false --depth.use_depth_loss=false 
  python3 evaluate.py --group=iphone --model=barf --yaml=barf_iphone --name=result_chair --data.scene=chair  --data.val_sub= --resume --depth.use_depth=false --depth.use_depth_loss=false 
  ```
  All the results will be stored in the directory `output/<GROUP>/<NAME>`.
  You may want to organize your experiments by grouping different runs in the same group.

  To train baseline models:
  - Full positional encoding: omit the `--barf_c2f` argument.
  - No positional encoding: add `--arch.posenc!`.
  - `--group=iphone` is a group that that does not use pose information in the data of the strayscanner.
  - If you want to evaluate a checkpoint at a specific iteration number, use `--resume=<ITER_NUMBER>` instead of just `--resume`.

  A video `vis.mp4` will also be created to visualize the optimization process.
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
