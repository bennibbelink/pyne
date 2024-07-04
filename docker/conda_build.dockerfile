ARG ubuntu_version=22.04

FROM ubuntu:${ubuntu_version} AS pyne-deps

# Ubuntu Setup
ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV HOME /root
RUN apt-get update \
    && apt-get install -y --fix-missing \
        wget \
        bzip2 \
        ca-certificates \
    && apt-get clean -y

RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh && \
    wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh

ENV PATH /opt/conda/bin:$PATH

# install python 3.10 because that's what apt uses
RUN conda update conda
RUN conda install "python=3.12"
RUN conda config --add channels conda-forge
RUN conda update -n base -c defaults conda
RUN conda install -y conda-libmamba-solver
RUN conda config --set solver libmamba
RUN conda install -y mamba
RUN conda uninstall -y conda-libmamba-solver
RUN conda config --set solver classic
RUN conda update -y --all && \
    mamba install -y \
                gxx_linux-64 \
                gcc_linux-64 \
                cmake \
                make \
                gfortran \
                libblas \
                liblapack \
                eigen \
                numpy \
                scipy \
                matplotlib \
                git \
                setuptools \
                pytest \
                pytables \
                jinja2 \
                cython \
                future \
                progress \
                meson \
                && \
    conda clean -y --all
RUN mkdir -p `python -m site --user-site`

ENV CC /opt/conda/bin/x86_64-conda_cos6-linux-gnu-gcc
ENV CXX /opt/conda/bin/x86_64-conda_cos6-linux-gnu-g++
ENV CPP /opt/conda/bin/x86_64-conda_cos6-linux-gnu-cpp

# install MOAB
RUN conda install "conda-forge::moab=5.5.1"

# install DAGMC
RUN conda update -n base conda
RUN mamba install conda-forge::dagmc

# install OpenMC
RUN mamba install conda-forge::openmc

# Build/Install PyNE from release branch
FROM pyne-deps AS pyne

# put conda on the path
ENV LD_LIBRARY_PATH /opt/conda/lib:$LD_LIBRARY_PATH

# make starting directory
RUN mkdir -p $HOME/opt
RUN echo "export PATH=$HOME/.local/bin:\$PATH" >> ~/.bashrc

ENV PYNE_MOAB_ARGS "--moab"
ENV PYNE_DAGMC_ARGS "--dagmc"

COPY . $HOME/opt/pyne
RUN cd $HOME/opt/pyne \
    && python setup.py install --user \
                                $PYNE_MOAB_ARGS $PYNE_DAGMC_ARGS \
                                --clean -j 3;
ENV PATH $HOME/.local/bin:$PATH
RUN cd $HOME \
    && nuc_data_make \
    && cd $HOME/opt/pyne/tests \
    && ./ci-run-tests.sh python3
    