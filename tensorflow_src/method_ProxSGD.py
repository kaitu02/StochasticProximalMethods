"""! @package method_ProxSGD

Implementation of ProxSGD algorithm presented in

* S. Ghadimi, G. Lan, and H. Zhang. **[Mini-batch stochastic approximation methods for nonconvex stochastic composite optimization](https://link.springer.com/article/10.1007/s10107-014-0846-1)**. Math. Program., 155(1-2):267–305, 2016.

The algorithm is used to solve the nonconvex composite problem
    
\f $ F(w) = E_{\zeta_i} [f(w,\zeta_i)] + g(w) \f $

which covers the finite sum as a special case

\f $ F(w) = \frac{1}{n} \sum_{i=1}^n (f_i(w)) + g(w) \f $

This algorithm is implemented specifically in the case \f$g(w) = \|w\|_1 \f$.

Copyright (c) 2019 Nhan H. Pham, Department of Statistics and Operations Research, University of North Carolina at Chapel Hill

Copyright (c) 2019 Quoc Tran-Dinh, Department of Statistics and Operations Research, University of North Carolina at Chapel Hill

Copyright (c) 2019 Lam M. Nguyen, IBM Research, Thomas J. Watson Research Center
Yorktown Heights

Copyright (c) 2019 Dzung T. Phan, IBM Research, Thomas J. Watson Research Center
Yorktown Heights
All rights reserved.

If you found this helpful and are using it within our software please cite the following publication:

* N. H. Pham, L. M. Nguyen, D. T. Phan, and Q. Tran-Dinh, **[ProxSARAH: An Efficient Algorithmic Framework for Stochastic Composite Nonconvex Optimization](https://arxiv.org/abs/1902.05679)**, _arXiv preprint arXiv:1902.05679_, 2019.

"""

import tensorflow as tf
import numpy as np
import random
import pandas as pd
import math

from utils import *


#==================================================================================================================
# ProxSGD

def Prox_SGD(x, y, x_train, y_train, x_test, y_test, batch_size, LRinit, LRprime, LR_COMP, LBD, MAX_TOTAL_EPOCH,\
        w_list, loss_operation, accuracy_operation, verbose = 1, log_enable = 1):

    """! ProxSGD algorithm

    Parameters
    ----------
    @param x : placeholder for input data
    @param y : placeholder for input label
    @param x_train : train data
    @param y_train : train label
    @param x_test : test data
    @param y_test : test label
    @param batch_size : batch size used to calculate batch gradient
    @param LRinit : learning rate
    @param LRprime : used for diminishing learning rate scheme
    @param LR_COMP : common learning rate used for gradient mapping squared norm comparsion between algorithms
    @param LBD : penalty parameter of the non-smooth objective
    @param MAX_TOTAL_EPOCH : the minimum number of epochs to run before termination
    @param w_list : list containing trainable parameters
    @param loss_operation : operation to evaluate loss
    @param prog_id : function pointer for difference of gradient nablaf(w') - nablaf(w)
    @param accuracy_operation : operation to evaluate accuracy
    @param verbose : specify verbosity level

            0 : silence

            1 : print iteration info

    @param log_enable : flag whether to compute and log data

    Returns
    -------
    @retval w : solution
    @retval hist_NumGrad : number of gradient evaluations history
    @retval hist_NumEpoch : history of epochs at which data were recorded
    @retval hist_TrainLoss : train loss history    
    @retval hist_GradNorm : squared norm of gradient mapping history
    @retval hist_MinGradNorm : minimum squared norm of gradient mapping history
    @retval hist_TrainAcc : train accuracy history
    @retval hist_TestAcc : test accuracy history
    """

    #=========================================#
    # setup

    ## operation for calculating gradient
    grad_list = tf.gradients(loss_operation, w_list)

    ## parameters used in algorithm update
    scale   = tf.placeholder(tf.float32)
    lr      = tf.placeholder(tf.float32)
    lbd     = tf.placeholder(tf.float32)

    ## variables for main updates
    v_list          = [tf.Variable(tf.zeros(list(w.get_shape())), dtype = tf.float32) for w in w_list]
    v0_list         = [tf.Variable(tf.zeros(list(w.get_shape())), dtype = tf.float32) for w in w_list]
    grad_map_list   = [tf.Variable(tf.zeros(list(w.get_shape())), dtype = tf.float32) for w in w_list]

    ## variables to hold norm square of gradient, gradient mapping and l1 norm of w
    norm_v0_sq          = tf.Variable(0.0)
    norm_v_sq           = tf.Variable(0.0)
    norm_grad_map_sq    = tf.Variable(0.0)
    norm_l1_w           = tf.Variable(0.0)

    ## supporting operations in main loop
    # operations used when calculating gradients
    ops_set_v_to_zero   = []
    ops_add_grad_to_v   = []
    ops_set_v0_to_zero  = []
    ops_add_grad_to_v0  = []

    # operations used when calculating norm of gradients
    ops_set_norm_v0_to_zero         = []
    ops_set_norm_v_to_zero          = []
    ops_set_norm_grad_map_to_zero   = []
    ops_set_norm_l1_w_to_zero       = []
    ops_calc_norm_v0_sq              = []
    ops_calc_norm_v_sq               = []
    ops_calc_norm_grad_map_sq        = []
    ops_calc_norm_l1_w               = []

    # operations for main algorithm update
    ops_update_w        = []
    ops_update_grad_map = []

    # assign operations
    for v, v0, w, grad, grad_map in zip(v_list, v0_list, w_list, grad_list, grad_map_list):

        # batch gradient operations
        ops_set_v_to_zero.append(v.assign(v*0))
        ops_add_grad_to_v.append(v.assign_add(scale*grad))

        # full gradient operations
        ops_set_v0_to_zero.append(v0.assign(v*0))
        ops_add_grad_to_v0.append(v0.assign_add(scale*grad))

        # calculate norm squares and l1 norm
        ops_set_norm_v0_to_zero.append(norm_v0_sq.assign(norm_v0_sq * 0))
        ops_set_norm_v_to_zero.append(norm_v_sq.assign(norm_v_sq * 0))        
        ops_set_norm_grad_map_to_zero.append(norm_grad_map_sq.assign(norm_grad_map_sq * 0))
        ops_set_norm_l1_w_to_zero.append(norm_l1_w.assign(norm_l1_w * 0))

        ops_calc_norm_v0_sq.append(norm_v0_sq.assign_add(tf.reduce_sum(tf.multiply(v0,v0))))
        ops_calc_norm_v_sq.append(norm_v_sq.assign_add(tf.reduce_sum(tf.multiply(v,v))))
        ops_calc_norm_grad_map_sq.append(norm_grad_map_sq.assign_add(tf.reduce_sum(tf.multiply(grad_map, grad_map))))
        ops_calc_norm_l1_w.append(norm_l1_w.assign_add(tf.reduce_sum(tf.abs(w))))

        # Iteration update
        ops_update_w.append(w.assign(prox_l1(w - lr*v, lbd*lr)))

        # update gradient mapping
        ops_update_grad_map.append(grad_map.assign((1/lr)*(w - prox_l1(w - lr*v0, lr * lbd))))
        
    ## group operations
    # Batch/Full gradient operations
    trainer_set_v_to_zero   = tf.group(*ops_set_v_to_zero)
    trainer_add_grad_to_v   = tf.group(*ops_add_grad_to_v)
    trainer_set_v0_to_zero  = tf.group(*ops_set_v0_to_zero)
    trainer_add_grad_to_v0  = tf.group(*ops_add_grad_to_v0)

    # calculate norm squares and l1 norm
    trainer_set_norm_v0_to_zero         = tf.group(*ops_set_norm_v0_to_zero)
    trainer_set_norm_v_to_zero          = tf.group(*ops_set_norm_v_to_zero)
    trainer_set_norm_grad_map_to_zero   = tf.group(*ops_set_norm_grad_map_to_zero)
    trainer_set_norm_l1_w_to_zero       = tf.group(*ops_set_norm_l1_w_to_zero)
    
    trainer_calc_norm_v0_sq              = tf.group(*ops_calc_norm_v0_sq)
    trainer_calc_norm_v_sq               = tf.group(*ops_calc_norm_v_sq)
    trainer_calc_norm_grad_map_sq        = tf.group(*ops_calc_norm_grad_map_sq)
    trainer_calc_norm_l1_w               = tf.group(*ops_calc_norm_l1_w)

    # Iteration update
    trainer_update_w        = tf.group(*ops_update_w)
    trainer_update_grad_map = tf.group(*ops_update_grad_map)

    #=========================================#
    # ProxSGD main algorithm

    # initialize history list
    hist_TrainLoss      = []
    hist_NumGrad        = []
    hist_NumEpoch       = []
    hist_GradNorm       = []
    hist_TrainAcc       = []
    hist_TestAcc        = []
    hist_MinGradNorm    = []
    w_sol               = []

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())

        # calculate sample size
        num_examples = len(x_train)

        # setup batch size to compute full/batch gradient
        bs = 128 
        num_batches_grad_full   = math.ceil( num_examples  / bs )
        num_batches_grad_batch  = math.ceil( batch_size  / bs )

        scale_full  = 1.0 / (num_batches_grad_full + 0.0)
        scale_batch = 1.0 / (num_batches_grad_batch + 0.0)
        
        # print initial message
        print("Training using ProxSGD...")
        print(
            ' {message:{fill}{align}{width}}'.format(message='',fill='=',align='^',width=63,),'\n',
            '{message:{fill}{align}{width}}'.format(message='eta',fill=' ',align='^',width=13,),'|',
            '{message:{fill}{align}{width}}'.format(message='eta_prime',fill=' ',align='^',width=13,),'|',
            '{message:{fill}{align}{width}}'.format(message='lambda',fill=' ',align='^',width=15,),'|',
            '{message:{fill}{align}{width}}'.format(message='Batch Size',fill=' ',align='^',width=13,),'\n',
            '{message:{fill}{align}{width}}'.format(message='',fill='-',align='^',width=63,)
        )
        print(
                '{:^14.2f}'.format(LRinit),'|',
                '{:^13.1f}'.format(LRprime),'|',
                '{:^15.3e}'.format(LBD),'|',
                '{:^12d}'.format(batch_size)
            )
        print(
            ' {message:{fill}{align}{width}}'.format(message='',fill='=',align='^',width=63,),'\n',
            )
        
        # initialize stats variables
        min_grad_map_norm_square   = 1.0e6

        # variables used to update number of gradient evaluations
        num_grad    = 0
        num_epoch   = 0

        # store previous time when message had been printed
        last_print_num_grad = num_grad

        # count total number of iterations
        total_iter = 0

        if log_enable:
            # calculate loss, test accuracy
            sess.run(trainer_set_norm_l1_w_to_zero)
            sess.run(trainer_calc_norm_l1_w)
            train_loss = sess.run(loss_operation, feed_dict={x: x_train, y: y_train}) + LBD * sess.run(norm_l1_w)
            train_accuracy = sess.run(accuracy_operation, feed_dict = {x: x_train, y: y_train})
            test_accuracy = sess.run(accuracy_operation, feed_dict = {x: x_test, y: y_test})

            # Compute full gradient
            sess.run(trainer_set_v0_to_zero)
            for j in range(num_batches_grad_full): 
                batch_X = x_train[bs*j:bs*(j+1)]
                batch_Y = y_train[bs*j:bs*(j+1)]
                sess.run(trainer_add_grad_to_v0, feed_dict={x: batch_X, y: batch_Y, scale: scale_full})

            # compute gradient mapping
            sess.run(trainer_update_grad_map, feed_dict = {lr: LR_COMP, lbd: LBD})
            sess.run(trainer_set_norm_grad_map_to_zero)
            sess.run(trainer_calc_norm_grad_map_sq)
            grad_map_norm_square = sess.run(norm_grad_map_sq)

            # update mins
            if grad_map_norm_square < min_grad_map_norm_square:
                min_grad_map_norm_square = grad_map_norm_square

            # print first time info
            if verbose:
                print(
                    ' {message:{fill}{align}{width}}'.format(message='',fill='=',align='^',width=87,),'\n',
                    '{message:{fill}{align}{width}}'.format(message='Epoch',fill=' ',align='^',width=15,),'|',
                    '{message:{fill}{align}{width}}'.format(message='Train Loss',fill=' ',align='^',width=15,),'|',
                    '{message:{fill}{align}{width}}'.format(message='||Grad Map||^2',fill=' ',align='^',width=15,),'|',
                    '{message:{fill}{align}{width}}'.format(message='Train Acc',fill=' ',align='^',width=15,),'|',
                    '{message:{fill}{align}{width}}'.format(message='Test Acc',fill=' ',align='^',width=15,),'\n',
                    '{message:{fill}{align}{width}}'.format(message='',fill='-',align='^',width=87,)
                )
                print(
                        '{:^16.4f}'.format(num_epoch),'|',
                        '{:^15.3e}'.format(train_loss),'|',
                        '{:^15.3e}'.format(grad_map_norm_square),'|',
                        '{:^15.5f}'.format(train_accuracy),'|',
                        '{:^13.5f}'.format(test_accuracy),'|',
                    )

            # update history
            hist_TrainLoss.append(train_loss)
            hist_GradNorm.append(np.asscalar(grad_map_norm_square))
            hist_MinGradNorm.append(min_grad_map_norm_square)
            hist_NumEpoch.append(num_epoch)
            hist_NumGrad.append(num_grad)
            hist_TrainAcc.append(train_accuracy)
            hist_TestAcc.append(test_accuracy)

            # update print time
            last_print_num_grad = num_grad
        
        # ProxSGD main loop
        while num_epoch < MAX_TOTAL_EPOCH:
            
            if batch_size == 1:
                # sample random index
                i = np.random.randint(0,num_examples)

                # extract sample
                x_sample = np.expand_dims(x_train[i], axis=0)
                y_sample = np.expand_dims(y_train[i], axis=0)

                # Compute batch gradient
                sess.run(trainer_set_v_to_zero)
                sess.run(trainer_add_grad_to_v, feed_dict={x: x_sample, y: y_sample, scale: 1.0})
                        
            else:
                # sample mini batch
                index = random.sample(range(num_examples), batch_size)

                # Compute batch gradient
                sess.run(trainer_set_v_to_zero)
                for j in range(num_batches_grad_batch): 
                    batch_X = x_train[index[bs*j:bs*(j+1)]]
                    batch_Y = y_train[index[bs*j:bs*(j+1)]]
                    sess.run(trainer_add_grad_to_v, feed_dict={x: batch_X, y: batch_Y, scale: scale_batch})
                    
            # update number of gradient evaluations
            num_grad += batch_size
            num_epoch = num_grad / num_examples

            # diminishing learning rate
            total_iter += 1
            LR = LRinit / (1.0 + LRprime*(total_iter//num_examples) )

            # ProxSGD Update
            sess.run(trainer_update_w, feed_dict={lr: LR, lbd: LBD})
            
            if log_enable and (num_grad - last_print_num_grad >= num_examples or num_epoch >= MAX_TOTAL_EPOCH):
                # calculate loss, test accuracy
                sess.run(trainer_set_norm_l1_w_to_zero)
                sess.run(trainer_calc_norm_l1_w)
                train_loss = sess.run(loss_operation, feed_dict={x: x_train, y: y_train}) + LBD * sess.run(norm_l1_w)
                train_accuracy = sess.run(accuracy_operation, feed_dict = {x: x_train, y: y_train})
                test_accuracy = sess.run(accuracy_operation, feed_dict = {x: x_test, y: y_test})

                # Compute full gradient
                sess.run(trainer_set_v0_to_zero)
                for j in range(num_batches_grad_full): 
                    batch_X = x_train[bs*j:bs*(j+1)]
                    batch_Y = y_train[bs*j:bs*(j+1)]
                    sess.run(trainer_add_grad_to_v0, feed_dict={x: batch_X, y: batch_Y, scale: scale_full})

                # Compute full gradient
                sess.run(trainer_set_v0_to_zero)
                for j in range(num_batches_grad_full): 
                    batch_X = x_train[bs*j:bs*(j+1)]
                    batch_Y = y_train[bs*j:bs*(j+1)]
                    sess.run(trainer_add_grad_to_v0, feed_dict={x: batch_X, y: batch_Y, scale: scale_full})
                
                # compute gradient mapping
                sess.run(trainer_update_grad_map, feed_dict = {lr: LR_COMP, lbd: LBD})
                sess.run(trainer_set_norm_grad_map_to_zero)
                sess.run(trainer_calc_norm_grad_map_sq)
                grad_map_norm_square = sess.run(norm_grad_map_sq)

                # update mins
                if grad_map_norm_square < min_grad_map_norm_square:
                    min_grad_map_norm_square = grad_map_norm_square

                # print info
                if verbose:
                    print(
                        '{:^16.4f}'.format(num_epoch),'|',
                        '{:^15.3e}'.format(train_loss),'|',
                        '{:^15.3e}'.format(grad_map_norm_square),'|',
                        '{:^15.5f}'.format(train_accuracy),'|',
                        '{:^13.5f}'.format(test_accuracy),'|',
                    )

                # update history
                hist_TrainLoss.append(train_loss)
                hist_GradNorm.append(np.asscalar(grad_map_norm_square))
                hist_MinGradNorm.append(min_grad_map_norm_square)
                hist_NumEpoch.append(num_epoch)
                hist_NumGrad.append(num_grad)
                hist_TrainAcc.append(train_accuracy)
                hist_TestAcc.append(test_accuracy)

                # update print time
                last_print_num_grad = num_grad

        #end main loop
        print(' {message:{fill}{align}{width}}'.format(message='',fill='=',align='^',width=87,))

        # save solution
        for w in w_list:
            w_sol.append(sess.run(w))

    return w_sol, hist_NumGrad, hist_NumEpoch, hist_TrainLoss, hist_GradNorm, hist_MinGradNorm, hist_TrainAcc, hist_TestAcc

#===============================================================================================================================
