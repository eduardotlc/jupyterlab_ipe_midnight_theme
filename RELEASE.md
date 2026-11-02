# Making a new release

Set the version, then build the sdist and wheel:

```bash
pip install build twine hatch
hatch version <new-version>   # updates package.json
jlpm clean:all
rm -rf dist
jlpm install
python -m build
```

Check the result and publish it:

```bash
twine check --strict dist/*
twine upload dist/*
```

To automate this with GitHub, the workflows in `.github/workflows` follow the
[Jupyter Releaser](https://github.com/jupyter-server/jupyter_releaser) process. Before using
them, configure PyPI trusted publishing and the secrets `publish-release.yml` references.
