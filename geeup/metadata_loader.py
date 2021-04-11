import csv
import logging
import re
import collections
import ast


ValidationResult = collections.namedtuple("ValidationResult", ["success", "keys"])


class IllegalPropertyName(Exception):
    pass


def validate_metadata_from_csv(path):
    """
    Check if metadata is ok
    :param path:
    :return: true / false
    """
    all_keys = []

    with open(path, mode="r") as metadata_file:
        logging.info("Running metatdata validator for %s", path)
        success = True
        reader = csv.reader(metadata_file)
        header = next(reader)

        if not properties_allowed(properties=header, validator=allowed_property_key):
            raise IllegalPropertyName("The header has illegal name.")

        for row in reader:
            all_keys.append(row[0])
            if not properties_allowed(properties=row, validator=allowed_property_value):
                success = False

        logging.info("Validation successful") if success else logging.error(
            "Validation failed"
        )

        return ValidationResult(success=success, keys=all_keys)


def load_metadata_from_csv(path):
    """
    Grabs properties from the give csv file. The csv should be organised as follows:
    filename (without extension), property1, property2, ...

    Example:
    id_no,class,category,binomial
    my_file_1,GASTROPODA,EN,Aaadonta constricta
    my_file_2,GASTROPODA,CR,Aaadonta irregularis

    The corresponding files are my_file_1.tif and my_file_2.tif.

    The program will turn the above into a json object:

    { id_no: my_file_1, class: GASTROPODA, category: EN, binomial: Aaadonta constricta},
    { id_no: my_file_2, class: GASTROPODA, category: CR, binomial: Aaadonta irregularis}

    :param path to csv:
    :return: dictionary of dictionaries
    """
    with open(path, mode="r") as metadata_file:
        reader = csv.reader(metadata_file)
        header = next(reader)

        if not properties_allowed(properties=header, validator=allowed_property_key):
            raise IllegalPropertyName()

        metadata = {}

        for row in reader:
            if properties_allowed(properties=row, validator=allowed_property_value):
                values = []
                for item in row:
                    try:
                        values.append(ast.literal_eval(item))
                    except (ValueError, SyntaxError) as e:
                        values.append(item)
                metadata[row[0]] = dict(zip(header, values))

        return metadata


def properties_allowed(properties, validator):
    return all(validator(prop) for prop in properties)


def allowed_property_value(prop):
    if prop:
        return True
    else:
        logging.warning("Illegal property: empty string or None")
        return False


def allowed_property_key(prop):
    google_special_properties = (
        "system:description",
        "system:provider_url",
        "system:tags",
        "system:time_end",
        "system:time_start",
        "system:title",
    )

    if prop in google_special_properties or re.match("^[A-Za-z0-9_]+$", prop):
        return True
    else:
        logging.warning(
            "Property name %s is invalid. Special properties [system:description, system:provider_url, "
            "system:tags, system:time_end, system:time_start, system:title] are allowed; other property "
            "keys must contain only letters, digits and underscores."
        )
        return False


def is_legal_gee_metadata(row):
    key = row[0]
    values = row[1:]
    re.match("^[A-Za-z0-9_]+$", " asss_sasa")
