import logging
from collections.abc import Iterable as IterableClass
from typing import Dict, List, Optional, Sequence, Union

import anndata
import numpy as np
import scipy.sparse as sp_sparse
import torch

from scvi import _CONSTANTS
from scvi.data import get_from_registry

logger = logging.getLogger(__name__)

Number = Union[int, float]


def parse_use_gpu_arg(
    use_gpu: Optional[Union[str, int, bool]] = None,
    return_device=True,
):
    """
    Parses the use_gpu arg in codebase.

    Returned gpus are is compatible with PytorchLightning's gpus arg.
    If return_device is True, will also return the device.

    Parameters
    ----------
    use_gpu
        Use default GPU if available (if None or True), or index of GPU to use (if int),
        or name of GPU (if str, e.g., `'cuda:0'`), or use CPU (if False).
    return_device
        If True, will return the torch.device of use_gpu.
    """
    gpu_available = torch.cuda.is_available()
    if (use_gpu is None and not gpu_available) or (use_gpu is False):
        gpus = 0
        device = torch.device("cpu")
    elif (use_gpu is None and gpu_available) or (use_gpu is True):
        current = torch.cuda.current_device()
        device = torch.device(current)
        gpus = [current]
    elif isinstance(use_gpu, int):
        device = torch.device(use_gpu)
        gpus = [use_gpu]
    elif isinstance(use_gpu, str):
        device = torch.device(use_gpu)
        # changes "cuda:0" to "0,"
        gpus = use_gpu.split(":")[-1] + ","
    else:
        raise ValueError("use_gpu argument not understood.")

    if return_device:
        return gpus, device
    else:
        return gpus


def scrna_raw_counts_properties(
    adata: anndata.AnnData,
    idx1: Union[List[int], np.ndarray],
    idx2: Union[List[int], np.ndarray],
    var_idx: Optional[Union[List[int], np.ndarray]] = None,
) -> Dict[str, np.ndarray]:
    """
    Computes and returns some statistics on the raw counts of two sub-populations.

    Parameters
    ----------
    adata
        AnnData object setup with `scvi`.
    idx1
        subset of indices describing the first population.
    idx2
        subset of indices describing the second population.
    var_idx
        subset of variables to extract properties from. if None, all variables are used.

    Returns
    -------
    type
        Dict of ``np.ndarray`` containing, by pair (one for each sub-population),
        mean expression per gene, proportion of non-zero expression per gene, mean of normalized expression.
    """
    data = get_from_registry(adata, _CONSTANTS.X_KEY)
    data1 = data[idx1]
    data2 = data[idx2]
    if var_idx is not None:
        data1 = data1[:, var_idx]
        data2 = data2[:, var_idx]

    mean1 = np.asarray((data1).mean(axis=0)).ravel()
    mean2 = np.asarray((data2).mean(axis=0)).ravel()
    nonz1 = np.asarray((data1 != 0).mean(axis=0)).ravel()
    nonz2 = np.asarray((data2 != 0).mean(axis=0)).ravel()

    key = "_scvi_raw_norm_scaling"
    if key not in adata.obs.keys():
        scaling_factor = 1 / np.asarray(data.sum(axis=1)).ravel().reshape(-1, 1)
        scaling_factor *= 1e4
        adata.obs[key] = scaling_factor.ravel()
    else:
        scaling_factor = adata.obs[key].to_numpy().ravel().reshape(-1, 1)

    if issubclass(type(data), sp_sparse.spmatrix):
        norm_data1 = data1.multiply(scaling_factor[idx1])
        norm_data2 = data2.multiply(scaling_factor[idx2])
    else:
        norm_data1 = data1 * scaling_factor[idx1]
        norm_data2 = data2 * scaling_factor[idx2]

    norm_mean1 = np.asarray(norm_data1.mean(axis=0)).ravel()
    norm_mean2 = np.asarray(norm_data2.mean(axis=0)).ravel()

    properties = dict(
        raw_mean1=mean1,
        raw_mean2=mean2,
        non_zeros_proportion1=nonz1,
        non_zeros_proportion2=nonz2,
        raw_normalized_mean1=norm_mean1,
        raw_normalized_mean2=norm_mean2,
    )
    return properties


def cite_seq_raw_counts_properties(
    adata: anndata.AnnData,
    idx1: Union[List[int], np.ndarray],
    idx2: Union[List[int], np.ndarray],
) -> Dict[str, np.ndarray]:
    """
    Computes and returns some statistics on the raw counts of two sub-populations.

    Parameters
    ----------
    adata
        AnnData object setup with `scvi`.
    idx1
        subset of indices describing the first population.
    idx2
        subset of indices describing the second population.

    Returns
    -------
    type
        Dict of ``np.ndarray`` containing, by pair (one for each sub-population),
        mean expression per gene, proportion of non-zero expression per gene, mean of normalized expression.
    """
    gp = scrna_raw_counts_properties(adata, idx1, idx2)
    protein_exp = get_from_registry(adata, _CONSTANTS.PROTEIN_EXP_KEY)

    nan = np.array([np.nan] * len(adata.uns["_scvi"]["protein_names"]))
    protein_exp = get_from_registry(adata, _CONSTANTS.PROTEIN_EXP_KEY)
    mean1_pro = np.asarray(protein_exp[idx1].mean(0))
    mean2_pro = np.asarray(protein_exp[idx2].mean(0))
    nonz1_pro = np.asarray((protein_exp[idx1] > 0).mean(0))
    nonz2_pro = np.asarray((protein_exp[idx2] > 0).mean(0))
    properties = dict(
        raw_mean1=np.concatenate([gp["raw_mean1"], mean1_pro]),
        raw_mean2=np.concatenate([gp["raw_mean2"], mean2_pro]),
        non_zeros_proportion1=np.concatenate([gp["non_zeros_proportion1"], nonz1_pro]),
        non_zeros_proportion2=np.concatenate([gp["non_zeros_proportion2"], nonz2_pro]),
        raw_normalized_mean1=np.concatenate([gp["raw_normalized_mean1"], nan]),
        raw_normalized_mean2=np.concatenate([gp["raw_normalized_mean2"], nan]),
    )

    return properties


def scatac_raw_counts_properties(
    adata: anndata.AnnData,
    idx1: Union[List[int], np.ndarray],
    idx2: Union[List[int], np.ndarray],
    var_idx: Optional[Union[List[int], np.ndarray]] = None,
) -> Dict[str, np.ndarray]:
    """
    Computes and returns some statistics on the raw counts of two sub-populations.

    Parameters
    ----------
    adata
        AnnData object setup with `scvi`.
    idx1
        subset of indices describing the first population.
    idx2
        subset of indices describing the second population.
    var_idx
        subset of variables to extract properties from. if None, all variables are used.

    Returns
    -------
    type
        Dict of ``np.ndarray`` containing, by pair (one for each sub-population).
    """
    data = get_from_registry(adata, _CONSTANTS.X_KEY)
    data1 = data[idx1]
    data2 = data[idx2]
    if var_idx is not None:
        data1 = data1[:, var_idx]
        data2 = data2[:, var_idx]
    mean1 = np.asarray((data1 > 0).mean(axis=0)).ravel()
    mean2 = np.asarray((data2 > 0).mean(axis=0)).ravel()
    properties = dict(emp_mean1=mean1, emp_mean2=mean2, emp_effect=(mean1 - mean2))
    return properties


def _get_var_names_from_setup_anndata(adata):
    """Gets var names by checking if using raw."""
    var_names = adata.var_names
    return var_names


def _get_batch_code_from_category(
    adata: anndata.AnnData, category: Sequence[Union[Number, str]]
):
    if not isinstance(category, IterableClass) or isinstance(category, str):
        category = [category]

    categorical_mappings = adata.uns["_scvi"]["categorical_mappings"]
    batch_mappings = categorical_mappings["_scvi_batch"]["mapping"]
    batch_code = []
    for cat in category:
        if cat is None:
            batch_code.append(None)
        elif cat not in batch_mappings:
            raise ValueError('"{}" not a valid batch category.'.format(cat))
        else:
            batch_loc = np.where(batch_mappings == cat)[0][0]
            batch_code.append(batch_loc)
    return batch_code
