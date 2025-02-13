"""File for development testing
"""


from xbridge.taxonomy_loader import Taxonomy

if __name__ == "__main__":
    # INPUT_PATH_3_3 = Path(__file__).parent / "tests" / "test_files" / "sample_3_3"
    # INSTANCE_PATH = Path.cwd() / "input" / "dora_sample.xbrl"
    # INSTANCE_PATH = Path(__file__).parent / "tests" / "test_files" /
    # "sample_3_2_phase1" / "test1_in.xbrl"
    TAXONOMY_PATH = "input/FullTaxonomy.zip"

    Taxonomy().load_modules(TAXONOMY_PATH)

    # start = time()
    # converter = Converter(INSTANCE_PATH)
    # initial = time()
    # print(converter.convert(output_path="output/"))
    # end = time()
    # print(f"Time to initialize: {initial - start}")
    # print(f"Time to convert: {end - initial}")
    # print(f"Total time: {end - start}")
