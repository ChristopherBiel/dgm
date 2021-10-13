from typing import Callable

import jax
import jax.numpy as jnp
from jax.experimental.stax import Identity

import wandb
from dgm.main.learn_system import LearnSystem
from dgm.schedules.betas import BetasType
from dgm.schedules.learning_rate import LearningRateType
from dgm.schedules.weight_decay import WeightDecayType
from dgm.utils.representatives import FeaturesToFeaturesType, TimeAndStatesToFeaturesType
from dgm.utils.representatives import KernelType, Optimizer, DynamicsModel, SimulatorType

Schedule = Callable[[int], float]

if __name__ == '__main__':
    kernel_seed = 0
    kernel_rng = jax.random.PRNGKey(kernel_seed)

    weight_decay = 1
    lr = 0.1
    seed = 0

    num_trajectories = 1
    num_points_on_trajectory = 100
    num_der_points = 100
    my_times = [jnp.linspace(0, 1, num_points_on_trajectory, dtype=jnp.float32) for _ in range(num_trajectories)]

    my_test_times = [jnp.linspace(0, 1, 200, dtype=jnp.float32) for _ in range(num_trajectories)]
    my_initial_conditions = [jnp.array([-2.5, 2.5, 2.5], dtype=jnp.float32)]
    my_stds_for_simulation = [jnp.array([1, 1, 1], dtype=jnp.float32) for _ in range(num_trajectories)]

    my_simulator_parameters = {'sigma': 10, 'rho': 28, 'beta': 8 / 3}

    track_wandb = True
    track_just_loss = True
    numerical_correction = 1e-3

    final_beta = 1
    transition_len = 500
    boundary = 1000

    num_iterations = boundary + 500

    run_dict = {
        'seed': seed,
        'data_generation': {
            'type': SimulatorType.LORENZ,
            'parameters': my_simulator_parameters,
            'noise': my_stds_for_simulation,
            'times': my_times,
            'test_times': my_test_times,
            'initial_conditions': my_initial_conditions
        },
        'smoother': {
            'kernel': {
                'type': KernelType.RBF_NO_VARIANCE,
                'kwargs': {
                    'feature_rng': kernel_rng,
                },
            },
            'core': {
                'type': TimeAndStatesToFeaturesType.NEURAL_NET,
                'kwargs': {'serial_input': [Identity]}
            },
            'kernel_core': {
                'type': FeaturesToFeaturesType.NEURAL_NET,
                'kwargs': {'serial_input': [Identity]}
            },
            'kernel_head': {
                'type': FeaturesToFeaturesType.NEURAL_NET,
                'kwargs': {'serial_input': [Identity]}
            },
            'mean_head': {
                'type': FeaturesToFeaturesType.ZERO,
                'kwargs': {'n_out': 3}
            }
        },
        'dynamics': {
            'type': DynamicsModel.JOINT_SMALL_DYNAMICS,
            'kwargs': {}
        },
        'betas': {
            'type': BetasType.TRANSITION_BETWEEN_VALUES,
            'kwargs': {'transition_start': 0, 'step_size': 0, 'decay_steps': transition_len,
                       'final_step_size': final_beta, 'power': 1, 'num_dim': 3},
        },
        'optimizer': {
            'type': Optimizer.ADAM,
            'learning_rate': {
                'type': LearningRateType.PIECEWISE_CONSTANT,
                'kwargs': {'boundaries': [boundary], 'values': [lr, 0.01]},
            },
        },
        'priors': {
            'wd_core': {
                'type': WeightDecayType.CONSTANT,
                'kwargs': {'step_size': weight_decay}
            },
            'wd_mean_head': {
                'type': WeightDecayType.CONSTANT,
                'kwargs': {'step_size': weight_decay}
            },
            'wd_kernel_core': {
                'type': WeightDecayType.CONSTANT,
                'kwargs': {'step_size': weight_decay}
            },
            'wd_kernel_head': {
                'type': WeightDecayType.CONSTANT,
                'kwargs': {'step_size': weight_decay}
            },
            'wd_pure_kernel': {
                'kernel_variance': {
                    'type': WeightDecayType.CONSTANT,
                    'kwargs': {'step_size': 0}
                },
                'kernel_lengthscale': {
                    'type': WeightDecayType.CONSTANT,
                    'kwargs': {'step_size': 0}
                },
                "observation_noise": {
                    'type': WeightDecayType.CONSTANT,
                    'kwargs': {'step_size': 0}
                }
            },
            'wd_dynamics': {
                'type': WeightDecayType.POLYNOMIAL_DECAY,
                'kwargs': {'step_size': 0, 'decay_steps': transition_len, 'final_step_size': weight_decay, 'power': 1}
            }
        },
        'logging': {
            'track_wandb': track_wandb,
            'track_just_loss': track_just_loss,
        },
        'numerical_correction': numerical_correction,
        'num_derivative_points_per_trajectory': num_der_points,
    }

    if track_wandb:
        wandb.init(
            project="Lorenz",
            config=run_dict,
            name='Single trajectory'
        )
        config = wandb.config

    model = LearnSystem(**run_dict)
    model.train(num_iterations)
