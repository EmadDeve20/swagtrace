import subprocess

from yaml_schema import ElementInfo, prepareAndFinal, SwagTaceTestFormat
from yaml_syntax.syntax import YamlSyntax


def project_banner_information(openapi:str, info: dict):

    print(f"OpenAPI: {openapi}")

    for k, v in info.items():
        print(f"{k}: {v}")


def prepare_and_final_test(prepare:prepareAndFinal):
    result = subprocess.run(prepare.execute, shell=True, text=True, capture_output=True)

    print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())
        raise RuntimeError(f"Failed prepare or final test: {result.stderr.strip()}")


def run_tags_cases(tags: dict[str, list[ElementInfo]]):

    for tag, _ in tags.items():
        print(f"test {tag} passed ...")


def main():

    yaml_serialized = YamlSyntax.from_file(SwagTaceTestFormat, "endpoints.yaml")

    test_sections:SwagTaceTestFormat = yaml_serialized.serialized_data

    project_banner_information(test_sections.openapi, test_sections.info)

    prepare_and_final_test(test_sections.prepare)

    run_tags_cases(test_sections.tags)

    prepare_and_final_test(test_sections.final)

