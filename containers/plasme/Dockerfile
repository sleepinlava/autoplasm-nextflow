# Build from the repository root: podman build -f containers/plasme/Dockerfile -t autoplasm-plasme:1.1 .
# The dedicated ignore file keeps database/work directories out of the context.
FROM docker.io/mambaorg/micromamba@sha256:b61105e17d910735a6cc3db188d349c67623306560328495424ddac551785599
COPY --chown=$MAMBA_USER:$MAMBA_USER containers/plasme/conda-linux-64.lock /tmp/plasme.lock
RUN micromamba create -y -n plasme -f /tmp/plasme.lock && micromamba clean --all --yes
ENV PATH=/opt/conda/envs/plasme/bin:$PATH
ENV ENV_NAME=plasme
COPY --chown=$MAMBA_USER:$MAMBA_USER bin/plasme_runtime.py /usr/local/bin/plasme_runtime.py
RUN python3 /usr/local/bin/plasme_runtime.py fix-elf /opt/conda/envs/plasme/lib/python3.9/site-packages/torch/lib/libtorch_cpu.so \
    && python3 -c 'import torch,numpy,pandas,Bio; assert torch.__version__ == "1.11.0"; assert not torch.cuda.is_available(); assert torch.tensor([[1.,2.],[3.,4.]]).matmul(torch.tensor([[5.,6.],[7.,8.]])).tolist() == [[19.,22.],[43.,50.]]'
USER root
# Nextflow's task metrics require ps even when the classifier itself does not.
RUN apt-get update && apt-get install -y --no-install-recommends procps && rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER
