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

- #### <span style="color:red">Strayscanner</span>
    Acquire data using [Strayscanner](https://docs.strayrobots.io/).
  
To generate the train/test data:
```
python data/process_strayscanner_data_image_resize.py --basedir <your_scenedir>
python data/process_strayscanner_data_image_resize.py --basedir ./data/strayscanner/chair 
```f_llff_data data/llff
  ```
  The `data` directory should contain the subdirectories `strayscanner` and `iphone`.
  If you already have the datasets downloaded, you can alternatively soft-link them within the `data` directory.

- #### <span style="color:red">Test your own sequence!</span>
  Place your scene directory somewhere. Follow the Strayscanner data structure.
  If you want to try CMNeRF on your own sequence, we provide a template data file in `data/strayscanner.py`, which is an example to read from a sequence captured by an iPhone 12 pro.   You should modify `get_image()` to read each image sample and set the raw image sizes (`self.raw_H`, `self.raw_W`) and focal length (`self.focal`) and (`self.pose`) w2c pose([right,down,forward]) and depth information (`self.gt_depth`, `self.confidence`)  according to your camera specs.  
Note: if you use this data format, make sure your `dataset_type` in the config file is set as `strayscanner`.

--------------------------------------

### Running the code

- #### CMNeRF models
  To train and evaluate CMNeRF:
  ```bash
  # <GROUP> and <NAME> can be set to your likes, while <SCENE> is specific to datasets
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
  - iphone 그룹은 초기 포즈를 identity로 설정한 것으로 strayscanner 그룹과 같은 데이터를 사용한다.

  A video `vis.mp4` will also be created to visualize the optimization process.
  
--------------------------------------
### Codebase structure

The main engine and network architecture in `model/barf.py` inherit those from `model/nerf.py`.
This codebase is structured so that it is easy to understand the actual parts BARF is extending from NeRF. 
(This code cannot be used to train origin NeRF.)
  
Some tips on using and understanding the codebase:
- The computation graph for forward/backprop is stored in `var` throughout the codebase.
- The losses are stored in `loss`. To add a new loss function, just implement it in `compute_loss()` and add its weight to `opt.loss_weight.<name>`. It will automatically be added to the overall loss and logged to Tensorboard.
- If you are using a multi-GPU machine, you can add `--gpu=<gpu_number>` to specify which GPU to use. Multi-GPU training/evaluation is currently not supported.
- To resume from a previous checkpoint, add `--resume=<ITER_NUMBER>`, or just `--resume` to resume from the latest checkpoint.
- (to be continued....)
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
