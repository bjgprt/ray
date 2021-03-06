from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import torch.nn as nn

from ray.rllib.models.pytorch.model import TorchModel
from ray.rllib.models.pytorch.misc import normc_initializer, valid_padding, \
    SlimConv2d, SlimFC
from ray.rllib.models.visionnet import _get_filter_config
from ray.rllib.utils.annotations import override


class VisionNetwork(TorchModel):
    """Generic vision network."""

    def __init__(self, obs_space, num_outputs, options):
        TorchModel.__init__(self, obs_space, num_outputs, options)
        filters = options.get("conv_filters")
        if not filters:
            filters = _get_filter_config(obs_space.shape)
        layers = []

        (w, h, in_channels) = obs_space.shape
        in_size = [w, h]
        for out_channels, kernel, stride in filters[:-1]:
            padding, out_size = valid_padding(in_size, kernel,
                                              [stride, stride])
            layers.append(
                SlimConv2d(in_channels, out_channels, kernel, stride, padding))
            in_channels = out_channels
            in_size = out_size

        out_channels, kernel, stride = filters[-1]
        layers.append(
            SlimConv2d(in_channels, out_channels, kernel, stride, None))
        self._convs = nn.Sequential(*layers)

        self._logits = SlimFC(
            out_channels, num_outputs, initializer=nn.init.xavier_uniform_)
        self._value_branch = SlimFC(
            out_channels, 1, initializer=normc_initializer())

    @override(TorchModel)
    def _forward(self, input_dict, hidden_state):
        features = self._hidden_layers(input_dict["obs"])
        logits = self._logits(features)
        value = self._value_branch(features).squeeze(1)
        return logits, features, value, hidden_state

    def _hidden_layers(self, obs):
        res = self._convs(obs.permute(0, 3, 1, 2))  # switch to channel-major
        res = res.squeeze(3)
        res = res.squeeze(2)
        return res
