# maug

`maug` is a package for multilingual data augmentation. It offers transformations focused on changing specific aspects of sentences, such as Named Entities, Numbers, etc.

# Usage

The `maug` package can be used as a command line interface (CLI) or by directly importing and calling the package Python API. To use `maug`, first install it by following these [instructions](#install).

## Command Line Interface

The CLI offers a way to read, transform, validate and write perturbed sentences to files. For more information, see the [full details](CLI.md).

### Single transform

To apply a single transform to a set of sentences, execute the following command:

```
$ augment io-read-lines -p <input_file> -l <input_lang_code> <transf_name> io-write-json -p <output_file>
```

> `<transf_name>` is the name of the transform to apply (see this [section](OPERATIONS.md#transforms) for a list of available transforms).
>
> `<input_file>` is a text file with one sentence per line.
>
> `<input_lang_code>` is a two character language code for the input sentences.
>
> `<output_file>` is a json file to be created with the transformed sentences.

### Multiple Transforms

To apply multiple transforms, just specify them in arbitrary order between the read and write operations:

```
$ augment io-read-lines -p <input_file> -l <input_lang_code> <transf_name_1> <transf_name_2> ... io-write-json -p <output_file>
```

### Multiple Input Files

To read from multiple input files, also specify them in arbitrary order:

```
$ augment io-read-lines -p <input_file_1> -l <input_lang_code_1> read-lines -p <input_file_2> -l <input_lang_code_2> ... <transf_name_1> <transf_name_2> ... io-write-json -p <output_file>
```

## Python API

TODO

# Install

To install this package, execute the following steps:

* Install the [poetry](https://python-poetry.org/docs/#installation) tool for dependency management.

* Clone this git repository and install the project.

```
$ git clone https://github.com/DuarteMRAlves/maug.git
$ cd maug
$ poetry install
```