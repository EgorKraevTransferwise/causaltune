import pandas as pd
import numpy as np
from auto_causality.utils import featurize


def amazon_reviews(rating="pos") -> pd.DataFrame:
    """loads amazon reviews dataset
    The dataset describes the impact of positive (or negative) reviews for products on Amazon on sales.
    The authors distinguish between items with more than three reviews (treated) and less than three
    reviews (untreated). As the rating given by reviews might impact sales, they divide the dataset
    into products with on average positive (more than 3 starts) or negative (less than three stars)
    reviews.
    The dataset consists of 305 covariates (doc2vec features of the review text), a binary treatment
    variable (more than 3 reviews vs less than three reviews) and a continuous outcome (sales).

    If used for academic purposes, please consider citing the authors:
    @inproceedings{rakesh2018linked,
        title={Linked Causal Variational Autoencoder for Inferring Paired Spillover Effects},
        author={Rakesh, Vineeth and Guo, Ruocheng and Moraffah, Raha and Agarwal, Nitin and Liu, Huan},
        booktitle={Proceedings of the 27th ACM International Conference on Information and Knowledge Management},
        pages={1679--1682},
        year={2018},
        organization={ACM}
    }
    Args:
        rating (str, optional): choose between positive ('pos') and negative ('neg') reviews. Defaults to 'pos'.

    Returns:
        pd.DataFrame: dataset with cols "treatment", "y_factual" and covariates "x1" to "x300"
    """
    try:
        assert rating in ["pos", "neg"]
    except AssertionError:
        print(
            "you need to specify which rating dataset you'd like to load. The options are 'pos' or 'neg'"
        )

    try:
        import gdown
    except ImportError:
        gdown = None

    if gdown:
        if rating == "pos":
            url = "https://drive.google.com/file/d/167CYEnYinePTNtKpVpsg0BVkoTwOwQfK/view?usp=sharing"
        elif rating == "neg":
            url = "https://drive.google.com/file/d/1b-MPNqxCyWSJE5uyn5-VJUwC8056HM8u/view?usp=sharing"
        gdown.download(url, "amazon_" + rating + ".csv", fuzzy=True)
        df = pd.read_csv("amazon_" + rating + ".csv")
        df.drop(df.columns[[2, 3, 4]], axis=1, inplace=True)
        df.columns = ["treatment", "y_factual"] + ["x_" + str(i) for i in range(1, 301)]
        return df
    else:
        print(
            f"""The Amazon dataset is hosted on google drive. As it's quite large, the gdown package is required to download
            the package automatically. The package can be installed via 'pip install gdown'.
            Alternatively, you can download it from the following link and store it in the datasets folder:
            {url}"""
        )


def synth_ihdp() -> pd.DataFrame:
    """loads IHDP dataset
    The Infant Health and Development Program (IHDP) dataset contains data on the impact of visits by specialists
    on the cognitive development of children. The dataset consists of 25 covariates describing various features
    of these children and their mothers, a binary treatment variable (visit/no visit) and a continuous outcome.

    If used for academic purposes, consider citing the authors:
    @article{hill2011,
        title={Bayesian nonparametric modeling for causal inference.},
        author={Hill, Jennifer},
        journal={Journal of Computational and Graphical Statistics},
        volume={20},
        number={1},
        pages={217--240},
        year={2011}
    }

    Returns:
        pd.DataFrame: dataset for causal inference with cols "treatment", "y_factual" and covariates "x1" to "x25"
    """
    # load raw data
    data = pd.read_csv(
        "https://raw.githubusercontent.com/AMLab-Amsterdam/CEVAE/master/datasets/IHDP/csv/ihdp_npci_1.csv",
        header=None,
    )
    col = [
        "treatment",
        "y_factual",
        "y_cfactual",
        "mu0",
        "mu1",
    ]
    for i in range(1, 26):
        col.append("x" + str(i))
    data.columns = col
    # drop the columns we don't care about
    ignore_patterns = ["y_cfactual", "mu"]
    ignore_cols = [c for c in data.columns if any([s in c for s in ignore_patterns])]
    data = data.drop(columns=ignore_cols)

    return data


def synth_acic(condition=1) -> pd.DataFrame:
    """loads data from ACIC Causal Inference Challenge 2016
    The dataset consists of 58 covariates, a binary treatment and a continuous response.
    There are 10 simulated pairs of treatment and response, which can be selected
    with the condition argument supplied to this function.

    If used for academic purposes, consider citing the authors:
    @article{dorie2019automated,
        title={Automated versus do-it-yourself methods for causal inference: Lessons learned from a
         data analysis competition},
        author={Dorie, Vincent and Hill, Jennifer and Shalit, Uri and Scott, Marc and Cervone, Dan},
        journal={Statistical Science},
        volume={34},
        number={1},
        pages={43--68},
        year={2019},
        publisher={Institute of Mathematical Statistics}
    }

    Args:
        condition (int): in [1,10], corresponds to 10 simulated treatment/response pairs. Defaults to 1.

    Returns:
        pd.DataFrame: dataset for causal inference with columns "treatment", "y_factual" and covariates "x_1" to "x_58"
    """

    covariates = pd.read_csv(
        """https://raw.githubusercontent.com/IBM/causallib/
        master/causallib/datasets/data/acic_challenge_2016/x.csv"""
    )
    url = f"""https://raw.githubusercontent.com/IBM/causallib/master/causallib/
    datasets/data/acic_challenge_2016/zymu_{condition}.csv"""
    z_y_mu = pd.read_csv(url)
    z_y_mu["y_factual"] = z_y_mu.apply(
        lambda row: row["y1"] if row["z"] else row["y0"], axis=1
    )
    data = pd.concat([z_y_mu["z"], z_y_mu["y_factual"], covariates], axis=1)
    data.rename(columns={"z": "treatment"}, inplace=True)

    return data


def preprocess_dataset(data: pd.DataFrame) -> tuple:
    """preprocesses dataset for causal inference

    Args:
        data (pd.DataFrame): a dataset for causal inference

    Returns:
        tuple: dataset, features_x, features_w, list of targets, name of treatment
    """

    # prepare the data

    treatment = "treatment"
    targets = ["y_factual"]  # it's good to allow multiple ones
    features = [c for c in data.columns if c not in [treatment] + targets]

    data[treatment] = data[treatment].astype(int)
    # this is a trick to bypass some DoWhy/EconML bugs
    data["random"] = np.random.randint(0, 2, size=len(data))

    used_df = featurize(
        data, features=features, exclude_cols=[treatment] + targets, drop_first=False,
    )
    used_features = [c for c in used_df.columns if c not in [treatment] + targets]

    # Let's treat all features as effect modifiers
    features_X = [f for f in used_features if f != "random"]
    features_W = [f for f in used_features if f not in features_X]

    return used_df, features_X, features_W, targets, treatment
