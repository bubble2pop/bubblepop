"""
main_train.py은 모델 학습을 진행하는 스크립트입니다.
e.g. https://github.com/wisdomify/wisdomify/blob/main/main_train.py
"""
import random
import torch
import wandb
import argparse
import numpy as np
import pytorch_lightning as pl
from transformers import BertTokenizer, BertModel
from BERT.datamodules import AnmSourceNERDataModule
from BERT.loaders import load_config
from BERT.models import BiLabelNER
from BERT.labels import ANM_LABELS, SOURCE_LABELS
from BERT.paths import ARTIFACTS_DIR, bi_label_ner_ckpt
from pytorch_lightning.loggers import WandbLogger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ver", type=str)
    args = parser.parse_args()
    config = load_config(args.ver)
    config.update(vars(args))  # command-line arguments 도 기록하기!
    # --- fix random seeds -- #
    torch.manual_seed(config['seed'])
    random.seed(config['seed'])
    np.random.seed(config['seed'])
    # --- prepare the model and the datamodule --- #
    tokenizer = BertTokenizer.from_pretrained(config['bert'])
    bert = BertModel.from_pretrained(config['bert'])
    model = BiLabelNER(bert=bert, lr=float(config['lr']), num_labels_pair=(len(ANM_LABELS), len(SOURCE_LABELS)))
    datamodule = AnmSourceNERDataModule(config, tokenizer)
    # --- instantiate the trainer  --- #
    logger = WandbLogger(log_model=False)
    with wandb.init(project="BERT", config=config) as run:
        trainer = pl.Trainer(max_epochs=config['max_epochs'],
                             log_every_n_steps=config['log_every_n_steps'],
                             gpus=torch.cuda.device_count(),
                             enable_checkpointing=False,
                             logger=logger)
        trainer.fit(model=model, datamodule=datamodule)
        # --- save the model locally, as push it to wandb as an artifact --- #
        model_path = bi_label_ner_ckpt(config['ver'])
        trainer.save_checkpoint(model_path)
        artifact = wandb.Artifact(name=model.name, type="model", metadata=config)
        artifact.add_file(model_path)
        run.log_artifact(artifact, aliases=["latest", config['ver']])


if __name__ == '__main__':
    main()
