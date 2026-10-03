"""
GeoNexa — CLIP Contrastive Loss Functions.

Implements the symmetric InfoNCE (CLIP-style) contrastive loss
with temperature scaling, label smoothing, and hard negative weighting.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class CLIPContrastiveLoss(nn.Module):
    """
    Symmetric CLIP contrastive loss (InfoNCE).

    Computes cross-entropy loss for both:
      - image → text matching (which text matches this image?)
      - text → image matching (which image matches this text?)

    The temperature parameter controls the sharpness of the softmax
    distribution — lower temperature = sharper (harder) distributions.
    """

    def __init__(
        self,
        temperature: float = 0.07,
        label_smoothing: float = 0.1,
        learnable_temperature: bool = True,
    ):
        super().__init__()
        self.label_smoothing = label_smoothing

        if learnable_temperature:
            # Log-parameterized learnable temperature (CLIP paper approach)
            self.log_temperature = nn.Parameter(
                torch.tensor(float(temperature)).log()
            )
        else:
            self.register_buffer(
                "log_temperature",
                torch.tensor(float(temperature)).log()
            )

    @property
    def temperature(self) -> torch.Tensor:
        return self.log_temperature.exp()

    def forward(
        self,
        image_features: torch.Tensor,
        text_features: torch.Tensor,
    ) -> dict:
        """
        Compute CLIP contrastive loss.

        Args:
            image_features: L2-normalized image embeddings (B, D).
            text_features: L2-normalized text embeddings (B, D).

        Returns:
            dict with:
                - loss: total loss (scalar)
                - loss_i2t: image-to-text loss
                - loss_t2i: text-to-image loss
                - temperature: current temperature value
                - accuracy_i2t: top-1 accuracy for image→text
                - accuracy_t2i: top-1 accuracy for text→image
        """
        batch_size = image_features.shape[0]
        device = image_features.device

        # Cosine similarity matrix scaled by temperature
        # (B, B) — each row i, col j is similarity between image_i and text_j
        logits = (image_features @ text_features.T) / self.temperature

        # Ground truth: diagonal entries are positive pairs
        labels = torch.arange(batch_size, device=device)

        # Symmetric cross-entropy loss
        loss_i2t = F.cross_entropy(
            logits, labels, label_smoothing=self.label_smoothing
        )
        loss_t2i = F.cross_entropy(
            logits.T, labels, label_smoothing=self.label_smoothing
        )
        loss = (loss_i2t + loss_t2i) / 2.0

        # Accuracy metrics
        with torch.no_grad():
            pred_i2t = logits.argmax(dim=1)
            pred_t2i = logits.T.argmax(dim=1)
            acc_i2t = (pred_i2t == labels).float().mean()
            acc_t2i = (pred_t2i == labels).float().mean()

        return {
            "loss": loss,
            "loss_i2t": loss_i2t.item(),
            "loss_t2i": loss_t2i.item(),
            "temperature": self.temperature.item(),
            "accuracy_i2t": acc_i2t.item(),
            "accuracy_t2i": acc_t2i.item(),
        }


class HardNegativeCLIPLoss(CLIPContrastiveLoss):
    """
    CLIP contrastive loss with in-batch hard negative emphasis.

    Adds extra weight to the hardest negative examples within each
    batch to accelerate learning of fine-grained distinctions
    (e.g., urban vs. bare soil, forest vs. agriculture).
    """

    def __init__(
        self,
        temperature: float = 0.07,
        label_smoothing: float = 0.1,
        hard_negative_weight: float = 2.0,
        learnable_temperature: bool = True,
    ):
        super().__init__(temperature, label_smoothing, learnable_temperature)
        self.hard_negative_weight = hard_negative_weight

    def forward(
        self,
        image_features: torch.Tensor,
        text_features: torch.Tensor,
    ) -> dict:
        """Compute loss with hard negative re-weighting."""
        batch_size = image_features.shape[0]
        device = image_features.device

        logits = (image_features @ text_features.T) / self.temperature
        labels = torch.arange(batch_size, device=device)

        # Create weight mask: upweight the hardest negatives
        with torch.no_grad():
            # Mask out the positive (diagonal)
            neg_mask = ~torch.eye(batch_size, dtype=torch.bool, device=device)

            # Find hardest negatives per row
            neg_logits = logits.clone()
            neg_logits[~neg_mask] = float("-inf")
            hardest_neg_idx = neg_logits.argmax(dim=1)

            # Create weight matrix (extra weight on hardest negatives)
            weights = torch.ones_like(logits)
            for i in range(batch_size):
                weights[i, hardest_neg_idx[i]] = self.hard_negative_weight

        # Weighted symmetric loss
        # We apply weights by scaling the logits for the hard negatives
        weighted_logits = logits * weights

        loss_i2t = F.cross_entropy(
            weighted_logits, labels, label_smoothing=self.label_smoothing
        )
        loss_t2i = F.cross_entropy(
            weighted_logits.T, labels, label_smoothing=self.label_smoothing
        )
        loss = (loss_i2t + loss_t2i) / 2.0

        with torch.no_grad():
            pred_i2t = logits.argmax(dim=1)
            pred_t2i = logits.T.argmax(dim=1)
            acc_i2t = (pred_i2t == labels).float().mean()
            acc_t2i = (pred_t2i == labels).float().mean()

        return {
            "loss": loss,
            "loss_i2t": loss_i2t.item(),
            "loss_t2i": loss_t2i.item(),
            "temperature": self.temperature.item(),
            "accuracy_i2t": acc_i2t.item(),
            "accuracy_t2i": acc_t2i.item(),
        }
