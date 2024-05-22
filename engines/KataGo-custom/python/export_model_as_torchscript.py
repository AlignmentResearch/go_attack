"""Exports PyTorch models as TorchScript models.
"""
import argparse
import os
from pathlib import Path
from typing import List, Optional, Tuple

import torch

import data_processing_pytorch
import load_model
import modelconfigs
from model_pytorch import Model


class EvalModel(torch.nn.Module):
    """Removes outputs that are only used during training.

    I (tomtseng) doubt that JIT is smart enough to optimize out parameters and
    calculations that are no longer used as a result of removing outputs, but we
    might as well remove unnecessary outputs regardless so that in the future we
    can choose to manually remove those parameters and calculations without
    changing the interface of the TorchScript model.
    """

    def __init__(self, model: torch.nn.Module):
        super(EvalModel, self).__init__()
        self.model = model

        module = (
            model.module
            if isinstance(model, torch.optim.swa_utils.AveragedModel)
            else model
        )
        has_optimistic_head = module.policy_head.conv2p.weight.shape[0] > 5
        # The optimistic policy head exists at channel 5. We need to output it
        # along with the self policy output at channel 0.
        policy_output_channels = [0, 5] if has_optimistic_head else [0]
        # We need to register policy_output_channels as a buffer instead of
        # defining+using it in forward(). Otherwise the TorchScript tracer saves
        # it as a tensor with a fixed device, i.e., it won't get moved when the
        # TorchScript model moves devices. Since tensor indices like
        # policy_output_channels should be on the same device that the indexed
        # tensor is on, an error will then occur if the TorchScript model is
        # executed on a different device than the device it was traced on.
        self.register_buffer(
            "policy_output_channels",
            torch.tensor(policy_output_channels),
            persistent=False,
        )

    def forward(self, input_spatial: torch.tensor, input_global: torch.tensor):
        # The output of self.model() is a tuple of tuples where the first item
        # of the outer tuple is the main head output.
        policy, value, miscvalue, moremiscvalue, ownership, _, _, _, _ = self.model(
            input_spatial, input_global
        )[0]
        return (
            policy[:, self.policy_output_channels],
            value,
            miscvalue[:, :4],
            moremiscvalue[:, :2],
            ownership,
        )


def get_device(gpu_idx: Optional[int]) -> torch.device:
    if gpu_idx is None:
        return torch.device("cpu")
    else:
        if not torch.cuda.is_available():
            raise RuntimeError(f"CUDA not available with this PyTorch")
        return torch.device("cuda", gpu_idx)


def get_model(
    checkpoint_file: str, use_swa: bool, device: torch.device
) -> Tuple[torch.nn.Module, List[int], List[int]]:
    model, swa_model, _ = load_model.load_model(
        checkpoint_file=checkpoint_file,
        use_swa=use_swa,
        device=device,
    )
    spatial_input_shape = model.bin_input_shape
    global_input_shape = model.global_input_shape
    if swa_model is not None:
        model = swa_model
    model = EvalModel(model)
    model.eval()
    return model, spatial_input_shape, global_input_shape


def get_model_input(
    spatial_input_shape: List[int], global_input_shape: List[int], device: torch.device
) -> Tuple[torch.tensor, torch.tensor]:
    return (
        torch.zeros(spatial_input_shape, device=device).unsqueeze(0),
        torch.zeros(global_input_shape, device=device).unsqueeze(0),
    )


def main():
    DESCRIPTION = """Exports a PyTorch model as a TorchScript model."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "-checkpoint", help="PyTorch checkpoint to export", required=True
    )
    parser.add_argument(
        "-export-dir",
        help="Directory to save output models to",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "-filename-prefix",
        help="Filename prefix to save to within directory",
        required=True,
    )
    parser.add_argument("-use-fp16", help="Export with float16", action="store_true")
    parser.add_argument("-use-swa", help="Use SWA model", action="store_true")
    parser.add_argument(
        "-gpu",
        help="GPU index to use for running model. Defaults to CPU if flag is not specified.",
        type=int,
    )
    args = parser.parse_args()

    device = get_device(args.gpu)
    model, spatial_input_shape, global_input_shape = get_model(
        checkpoint_file=args.checkpoint, use_swa=args.use_swa, device=device
    )
    input_batch = get_model_input(
        spatial_input_shape=spatial_input_shape,
        global_input_shape=global_input_shape,
        device=device,
    )
    if args.use_fp16:
        model.half()
        input_batch = tuple(x.half() for x in input_batch)

    with torch.no_grad():
        traced_script_module = torch.jit.trace(func=model, example_inputs=input_batch)
    traced_script_module.cpu()

    destination = args.export_dir / f"{args.filename_prefix}.pt"
    traced_script_module.save(destination)
    print("Model saved to", destination)


if __name__ == "__main__":
    main()
