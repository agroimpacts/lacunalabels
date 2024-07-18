# A region-wide, multi-year set of crop field boundary labels for Africa


This repository hosts the analytical code and pointers to datasets
resulting from a project to generate a continent-wide set of crop field
labels for Africa covering the years 2017-2023. The data are intended
for training and assessing machine learning models that can be used to
map agricultural fields over large areas and multiple years.

The project was funded by the [Lacuna Fund](https://lacunafund.org/),
and led by [Farmerline](https://farmerline.co/), in collaboration with
[Spatial Collective](https://spatialcollective.com/) and the
[Agricultural Impacts Research Group](agroimpacts.info) at [Clark
University](https://www.clarku.edu/departments/geography/).

Please refer to the [technical
report](notebooks/report/technical-report.pdf) for more details on the
methods used to develop the dataset, an analysis of label quality, and
usage guidelines. The report and additional documents, analyses, and
demonstration code used to develop labels by cloning the repository:

``` bash
git clone git@github.com:agroimpacts/lacunalabels.git
cd lacunalabels
pip install -e .
```

Please see the next sections for details on accessing the imagery and
label data.

## Access and usage

The imagery and labels can be obtained either from
[Zenodo](https://zenodo.org/records/11060871) or the [Registry of Open
Data on AWS](https://registry.opendata.aws/), and may used in accordance
with Planet’s [participant license agreement for the NICFI
contract](https://assets.planet.com/docs/Planet_ParticipantLicenseAgreement_NICFI.pdf).
The code used to annotate and analyze the data is available under an
[Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0).

### Data on AWS

The data are in the bucket `s3://africa-field-boundary-labels` in the
`us-west-2` region, and are organized as follows:

<table>
<colgroup>
<col style="width: 5%" />
<col style="width: 94%" />
</colgroup>
<thead>
<tr class="header">
<th>Prefix/key</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>imagery/</td>
<td><p>Contains 4 band Planet image chips in geotiff format, named as
follows:</p>
<p>XX1234567890_YYYY-MM.tif</p>
<p>Representing a grid identifier and the image acquisition date and
month</p></td>
</tr>
<tr class="even">
<td>labels/</td>
<td><p>A set of 3-class labels in geotiff format, named as:</p>
<p>XX1234567890_123456_YYYY-MM.tif</p>
<p>Representing a grid identifier, a labelling assignment identifier,
and month and year of imagery being labelled.</p>
<p>These labels represent one possible set from a larger number of
labelling assignments, which were created using <a
href="https://github.com/agroimpacts/lacunalabels/blob/devel/notebooks/image-processing/label-chips.ipynb">the
demonstration notebook</a> provided in this repository.</p></td>
</tr>
<tr class="odd">
<td>label-catalog-filtered.csv</td>
<td>Details of each labeling assignment for the subset developed using
the demonstration notebook, including information on label quality.</td>
</tr>
<tr class="even">
<td>mapped_fields_final.parquet</td>
<td>The original digitized field boundaries collected on the Planet
imagery, in geoparquet format. These can be used together with the image
chips, the code provided in the <a
href="https://github.com/agroimpacts/lacunalabels/blob/devel/notebooks/image-processing/label-chips.ipynb">demonstration
notebook</a>, the full labelling assignment (<a
href="https://github.com/agroimpacts/lacunalabels/blob/main/data/interim/label_catalog_allclasses.csv">label_catalog_allclasses.csv</a>)
and the image chip catalog (image_chip_catalog.csv) to make different
subsets of labels.</td>
</tr>
</tbody>
</table>

To access the data, use the AWS CLI to download the data to a local
directory. We recommend making a new directory called “data” in your
home directory, changing into that, and then using the `sync` function,
as follows (note: this assumes a \*nix-based terminal.

``` bash
cd ~
mkdir data
cd data
aws s3 sync s3://africa-field-boundary-labels/ . --dryrun
aws s3 sync s3://africa-field-boundary-labels/ . 
```

If the second to last line previews a successful download, run the last
line, which will download all data on the bucket into your directory.

The AWS S3 console can also be used to download the data.

### Data on Zenodo

The image chips and geoparquet file can de downloaded directly from the
[Zenodo link](https://zenodo.org/records/11060871), or from the
[Registry of Open Data on AWS](https://registry.opendata.aws/).

## Citation

Please cite the dataset as follows:

Wussah, A., Asipunu, M., Gathigi, M., Kovačič, P., Muhando, J., Addai,
F., Akakpo, E.S., Allotey, M., Amkoya, P., Amponsem, E., Dadon, K.D.,
Gyan, V., Harrison X.G., Heltzel, E., Juma, C., Mdawida, R., Miroyo, A.,
Mucha, J., Mugami, J., Mwawaza, F., Nyarko, D., Oduor, P., Ohemeng, K.,
Segbefia, S.I.D., Tumbula, T., Wambua, F., Yeboah, F., Estes, L.D.,
2024. A region-wide, multi-year set of crop field boundary labels for
Africa. Dataset on Zenodo. DOI 10.5281/zenodo.11060870.

![](notebooks/report/images/fig-fldareamap-1.png)
