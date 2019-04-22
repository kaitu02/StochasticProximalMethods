# StochasticProximalMethods


## Introduction


This package is the implementation of ProxSARAH algorithm and its variants along with other stochastic proximal gradient algorithms including ProxSVRG, ProxSpiderBoost, ProxSGD, and ProxGD to solve the stochastic composite, nonconvex, and possibly nonsmooth optimization problem which covers the composite finite-sum minimization problem as a special case.

## Code Usage

We hope that this program will be useful to others, and we would like to hear about your experience with it. If you found it helpful and are using it within our software please cite the following publication:

* N. H. Pham, L. M. Nguyen, D. T. Phan, and Q. Tran-Dinh, **[ProxSARAH: An Efficient Algorithmic Framework for Stochastic Composite Nonconvex Optimization](https://arxiv.org/abs/1902.05679)**, _arXiv preprint arXiv:1902.05679_, 2019.

Feel free to send feedback and questions about the package to our maintainer Nhan H. Pham at <nhanph@live.unc.edu>.

## Dependencies

The code is tested under Python 3.6.3 and Tensorflow 1.12. 

For Tensorflow, you can follow the tutorial [here](https://www.tensorflow.org/install) to install.

It also requires additional packages if you do not have them

* argParser: for argument parsing
* matplotlib: for plotting
* sklearn: for normalizing input data
* keras: for loading datasets and other utility functions

```
pip install argParser matplotlib sklearn keras
```

## How to run

1. Understanding the argument:
	There are several arguments needed to run the script for each example. The main ones include

| Argument     | Description                   |
| -------------|:-----------------------------:| 
| -h           | print help message            |
| -a           | select algorithm: from 1 to 4 |
| -so          | select ProxSARAH variants            | 
| -ne          | number of total epochs to run |

More information can be found by running the corresponding example script with option -h
```python
python example_neural_net_[1 or 2].py -h
```

2. Running the examples:
	There are two example scripts that correspond to two examples in the paper. You can follow the command below to run:


```python
python example_neural_net_[1 or 2].py -d mnist -a 1234 -so 2345 -b 250 -ne 15
```
