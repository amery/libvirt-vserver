#!/usr/bin/python

#
# esx_vi_generator.py: generates most of the SOAP type mapping code
#
# Copyright (C) 2010 Matthias Bolte <matthias.bolte@googlemail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
#

import sys
import os
import os.path






class Property:
    OCCURRENCE__REQUIRED_ITEM = "r"
    OCCURRENCE__REQUIRED_LIST = "rl"
    OCCURRENCE__OPTIONAL_ITEM = "o"
    OCCURRENCE__OPTIONAL_LIST = "ol"
    OCCURRENCE__IGNORED = "i"

    valid_occurrences = [OCCURRENCE__REQUIRED_ITEM,
                         OCCURRENCE__REQUIRED_LIST,
                         OCCURRENCE__OPTIONAL_ITEM,
                         OCCURRENCE__OPTIONAL_LIST,
                         OCCURRENCE__IGNORED]

    def __init__(self, type, name, occurrence):
        self.type = type
        self.name = name
        self.occurrence = occurrence

    def is_enum(self):
        global predefined_enums
        global enums_by_name

        return self.type in predefined_enums or self.type in enums_by_name

    def generate_struct_member(self):
        if self.occurrence == Property.OCCURRENCE__IGNORED:
            return "    /* FIXME: %s is currently ignored */\n" % self.name
        else:
            string = "    %s%s; " % (self.get_type_string(), self.name)

            while len(string) < 59:
                string += " "

            return string + "/* %s */\n" % self.get_occurrence_string()

    def generate_free_code(self):
        if self.type == "String" and \
           self.occurrence not in [Property.OCCURRENCE__REQUIRED_LIST,
                                   Property.OCCURRENCE__OPTIONAL_LIST,
                                   Property.OCCURRENCE__IGNORED]:
            return "    VIR_FREE(item->%s);\n" % self.name
        elif self.is_enum():
            return ""
        else:
            if self.occurrence == Property.OCCURRENCE__IGNORED:
                return "    /* FIXME: %s is currently ignored */\n" % self.name
            else:
                return "    esxVI_%s_Free(&item->%s);\n" % (self.type, self.name)

    def generate_validate_code(self):
        if self.occurrence in [Property.OCCURRENCE__REQUIRED_ITEM,
                               Property.OCCURRENCE__REQUIRED_LIST]:
            return "    ESX_VI__TEMPLATE__PROPERTY__REQUIRE(%s)\n" % self.name
        elif self.occurrence == Property.OCCURRENCE__IGNORED:
            return "    /* FIXME: %s is currently ignored */\n" % self.name
        else:
            return ""

    def generate_deep_copy_code(self):
        if self.occurrence == Property.OCCURRENCE__IGNORED:
            return "    /* FIXME: %s is currently ignored */\n" % self.name
        elif self.occurrence in [Property.OCCURRENCE__REQUIRED_LIST,
                                 Property.OCCURRENCE__OPTIONAL_LIST]:
            return "    ESX_VI__TEMPLATE__PROPERTY__DEEP_COPY_LIST(%s, %s)\n" % (self.type, self.name)
        elif self.type == "String":
            return "    ESX_VI__TEMPLATE__PROPERTY__DEEP_COPY_VALUE(String, %s)\n" % self.name
        else:
            return "    ESX_VI__TEMPLATE__PROPERTY__DEEP_COPY(%s, %s)\n" % (self.type, self.name)

    def generate_serialize_code(self):
        if self.occurrence == Property.OCCURRENCE__IGNORED:
            return "    /* FIXME: %s is currently ignored */\n" % self.name
        elif self.occurrence in [Property.OCCURRENCE__REQUIRED_LIST,
                                 Property.OCCURRENCE__OPTIONAL_LIST]:
            return "    ESX_VI__TEMPLATE__PROPERTY__SERIALIZE_LIST(%s, %s)\n" % (self.type, self.name)
        elif self.type == "String":
            return "    ESX_VI__TEMPLATE__PROPERTY__SERIALIZE_VALUE(String, %s)\n" % self.name
        else:
            return "    ESX_VI__TEMPLATE__PROPERTY__SERIALIZE(%s, %s)\n" % (self.type, self.name)

    def generate_deserialize_code(self):
        if self.occurrence == Property.OCCURRENCE__IGNORED:
            return "    ESX_VI__TEMPLATE__PROPERTY__DESERIALIZE_IGNORE(%s) /* FIXME */\n" % self.name
        elif self.occurrence in [Property.OCCURRENCE__REQUIRED_LIST,
                                 Property.OCCURRENCE__OPTIONAL_LIST]:
            return "    ESX_VI__TEMPLATE__PROPERTY__DESERIALIZE_LIST(%s, %s)\n" % (self.type, self.name)
        elif self.type == "String":
            return "    ESX_VI__TEMPLATE__PROPERTY__DESERIALIZE_VALUE(String, %s)\n" % self.name
        else:
            return "    ESX_VI__TEMPLATE__PROPERTY__DESERIALIZE(%s, %s)\n" % (self.type, self.name)

    def get_type_string(self):
        if self.type == "String" and \
           self.occurrence not in [Property.OCCURRENCE__REQUIRED_LIST,
                                   Property.OCCURRENCE__OPTIONAL_LIST]:
            return "char *"
        elif self.is_enum():
            return "esxVI_%s " % self.type
        else:
            return "esxVI_%s *" % self.type

    def get_occurrence_string(self):
        if self.occurrence == Property.OCCURRENCE__REQUIRED_ITEM:
            return "required"
        elif self.occurrence == Property.OCCURRENCE__REQUIRED_LIST:
            return "required, list"
        elif self.occurrence == Property.OCCURRENCE__OPTIONAL_ITEM:
            return "optional"
        elif self.occurrence == Property.OCCURRENCE__OPTIONAL_LIST:
            return "optional, list"

        raise ValueError("unknown cardinality value '%s'" % self.cardinality)








class Object:
    FEATURE__DYNAMIC_CAST = (1 << 1)
    FEATURE__LIST         = (1 << 2)
    FEATURE__DEEP_COPY    = (1 << 3)
    FEATURE__ANY_TYPE     = (1 << 4)
    FEATURE__SERIALIZE    = (1 << 5)
    FEATURE__DESERIALIZE  = (1 << 6)

    def __init__(self, name, extends, properties, features = 0, extended_by = None):
        self.name = name
        self.extends = extends
        self.features = features | Object.FEATURE__SERIALIZE | Object.FEATURE__DESERIALIZE
        self.properties = properties
        self.extended_by = extended_by

        self.properties_by_name = {}

        for property in self.properties:
            self.properties_by_name[property.name] = property

    def generate_struct_members(self, add_banner = False, struct_gap = False):
        global objects_by_name
        members = ""

        if self.extends is None:
            struct_gap = True
            string = "    esxVI_Type _type; "

            while len(string) < 59:
                string += " "

            members += string + "/* required */\n"

        if struct_gap and self.extends is None:
            members += "\n"

        if self.extends is not None:
            members += objects_by_name[self.extends].generate_struct_members(add_banner = True, struct_gap = False) + "\n"

        if self.extends is not None or add_banner:
            members += "    /* %s */\n" % self.name

        for property in self.properties:
            members += property.generate_struct_member()

        if len(self.properties) < 1:
            members += "    /* no properties */\n"

        return members

    def generate_free_code(self, add_banner = False):
        global objects_by_name
        source = ""

        if self.extends is not None:
            source += objects_by_name[self.extends].generate_free_code(add_banner = True) + "\n"

        if self.extends is not None or add_banner:
            source += "    /* %s */\n" % self.name

        if len(self.properties) < 1:
            source += "    /* no properties */\n"
        else:
            string = ""

            for property in self.properties:
                string += property.generate_free_code()

            if len(string) < 1:
                source += "    /* no properties to be freed */\n"
            else:
                source += string

        return source

    def generate_validate_code(self, add_banner = False):
        global objects_by_name
        source = ""

        if self.extends is not None:
            source += objects_by_name[self.extends].generate_validate_code(add_banner = True) + "\n"

        if self.extends is not None or add_banner:
            source += "    /* %s */\n" % self.name

        if len(self.properties) < 1:
            source += "    /* no properties */\n"
        else:
            string = ""

            for property in self.properties:
                string += property.generate_validate_code()

            if len(string) < 1:
                source += "    /* no required properties */\n"
            else:
                source += string

        return source

    def generate_dynamic_cast_code(self):
        global objects_by_name
        source = ""

        if self.extended_by is not None:
            source += "    /* %s */\n" % self.name

            for extended_by in self.extended_by:
                source += "    ESX_VI__TEMPLATE__DYNAMIC_CAST__ACCEPT(%s)\n" % extended_by

            for extended_by in self.extended_by:
                source += objects_by_name[extended_by].generate_dynamic_cast_code()

        return source

    def generate_deep_copy_code(self, add_banner = False):
        global objects_by_name
        source = ""

        if self.extends is not None:
            source += objects_by_name[self.extends].generate_deep_copy_code(add_banner = True) + "\n"

        if self.extends is not None or add_banner:
            source += "    /* %s */\n" % self.name

        if len(self.properties) < 1:
            source += "    /* no properties */\n"
        else:
            string = ""

            for property in self.properties:
                string += property.generate_deep_copy_code()

            if len(string) < 1:
                source += "    /* no properties to be deep copied */\n"
            else:
                source += string

        return source

    def generate_serialize_code(self, add_banner = False):
        global objects_by_name
        source = ""

        if self.extends is not None:
            source += objects_by_name[self.extends].generate_serialize_code(add_banner = True) + "\n"

        if self.extends is not None or add_banner:
            source += "    /* %s */\n" % self.name

        if len(self.properties) < 1:
            source += "    /* no properties */\n"
        else:
            for property in self.properties:
                source += property.generate_serialize_code()

        return source

    def generate_deserialize_code(self, add_banner = False):
        global objects_by_name
        source = ""

        if self.extends is not None:
            source += objects_by_name[self.extends].generate_deserialize_code(add_banner = True) + "\n"

        if self.extends is not None or add_banner:
            source += "    /* %s */\n" % self.name

        if len(self.properties) < 1:
            source += "    /* no properties */\n"
        else:
            for property in self.properties:
                source += property.generate_deserialize_code()

        return source

    def generate_typedef(self):
        return "typedef struct _esxVI_%s esxVI_%s;\n" % (self.name, self.name)

    def generate_typeenum(self):
        return "    esxVI_Type_%s,\n" % self.name

    def generate_typetostring(self):
        string = "          case esxVI_Type_%s:\n" % self.name
        string += "            return \"%s\";\n\n" % self.name

        return string

    def generate_typefromstring(self):
        string =  "           else if (STREQ(type, \"%s\")) {\n" % self.name
        string += "               return esxVI_Type_%s;\n" % self.name
        string += "           }\n"

        return string

    def generate_header(self):
        header = "/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *\n"
        header += " * VI Type: %s\n" % self.name

        if self.extends is not None:
            header += " *          extends %s\n" % self.extends

        first = True

        if self.extended_by is not None:
            for extended_by in self.extended_by:
                if first:
                    header += " *          extended by %s\n" % extended_by
                    first = False
                else:
                    header += " *                      %s\n" % extended_by

        header += " */\n\n"

        # struct
        header += "struct _esxVI_%s {\n" % self.name

        if self.features & Object.FEATURE__LIST:
            string = "    esxVI_%s *_next; " % self.name
        else:
            string = "    esxVI_%s *_unused; " % self.name

        while len(string) < 59:
            string += " "

        header += string + "/* optional */\n"

        header += self.generate_struct_members(struct_gap = True)

        header += "};\n\n"

        # functions
        header += "int esxVI_%s_Alloc(esxVI_%s **item);\n" % (self.name, self.name)
        header += "void esxVI_%s_Free(esxVI_%s **item);\n" % (self.name, self.name)
        header += "int esxVI_%s_Validate(esxVI_%s *item);\n" % (self.name, self.name)

        if self.features & Object.FEATURE__DYNAMIC_CAST:
            if self.extended_by is not None or self.extends is not None:
                header += "esxVI_%s *esxVI_%s_DynamicCast(void *item);\n" % (self.name, self.name)
            else:
                report_error("cannot add dynamic cast support for an untyped object")

        if self.features & Object.FEATURE__LIST:
            header += "int esxVI_%s_AppendToList(esxVI_%s **list, esxVI_%s *item);\n" % (self.name, self.name, self.name)

        if self.features & Object.FEATURE__DEEP_COPY:
            header += "int esxVI_%s_DeepCopy(esxVI_%s **dst, esxVI_%s *src);\n" % (self.name, self.name, self.name)

            if self.features & Object.FEATURE__LIST:
                header += "int esxVI_%s_DeepCopyList(esxVI_%s **dstList, esxVI_%s *srcList);\n" % (self.name, self.name, self.name)

        if self.features & Object.FEATURE__ANY_TYPE:
            header += "int esxVI_%s_CastFromAnyType(esxVI_AnyType *anyType, esxVI_%s **item);\n" % (self.name, self.name)

            if self.features & Object.FEATURE__LIST:
                header += "int esxVI_%s_CastListFromAnyType(esxVI_AnyType *anyType, esxVI_%s **list);\n" % (self.name, self.name)

        if self.features & Object.FEATURE__SERIALIZE:
            header += "int esxVI_%s_Serialize(esxVI_%s *item, const char *element, virBufferPtr output);\n" % (self.name, self.name)

            if self.features & Object.FEATURE__LIST:
                header += "int esxVI_%s_SerializeList(esxVI_%s *list, const char *element, virBufferPtr output);\n" % (self.name, self.name)

        if self.features & Object.FEATURE__DESERIALIZE:
            header += "int esxVI_%s_Deserialize(xmlNodePtr node, esxVI_%s **item);\n" % (self.name, self.name)

            if self.features & Object.FEATURE__LIST:
                header += "int esxVI_%s_DeserializeList(xmlNodePtr node, esxVI_%s **list);\n" % (self.name, self.name)

        header += "\n\n\n"

        return header

    def generate_source(self):
        source = "/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *\n"
        source += " * VI Type: %s\n" % self.name

        if self.extends is not None:
            source += " *          extends %s\n" % self.extends

        first = True

        if self.extended_by is not None:
            for extended_by in self.extended_by:
                if first:
                    source += " *          extended by %s\n" % extended_by
                    first = False
                else:
                    source += " *                      %s\n" % extended_by

        source += " */\n\n"

        # functions
        source += "/* esxVI_%s_Alloc */\n" % self.name
        source += "ESX_VI__TEMPLATE__ALLOC(%s)\n\n" % self.name

        # free
        if self.extended_by is None:
            source += "/* esxVI_%s_Free */\n" % self.name
            source += "ESX_VI__TEMPLATE__FREE(%s,\n" % self.name
            source += "{\n"

            if self.features & Object.FEATURE__LIST:
                source += "    esxVI_%s_Free(&item->_next);\n\n" % self.name

            source += self.generate_free_code()

            source += "})\n\n"
        else:
            source += "/* esxVI_%s_Free */\n" % self.name
            source += "ESX_VI__TEMPLATE__DYNAMIC_FREE(%s,\n" % self.name
            source += "{\n"

            for extended_by in self.extended_by:
                source += "    ESX_VI__TEMPLATE__DISPATCH__FREE(%s)\n" % extended_by

            source += "},\n"
            source += "{\n"

            if self.features & Object.FEATURE__LIST:
                source += "    esxVI_%s_Free(&item->_next);\n\n" % self.name

            source += self.generate_free_code()

            source += "})\n\n"

        # validate
        source += "/* esxVI_%s_Validate */\n" % self.name
        source += "ESX_VI__TEMPLATE__VALIDATE(%s,\n" % self.name
        source += "{\n"

        source += self.generate_validate_code()

        source += "})\n\n"

        # dynamic cast
        if self.features & Object.FEATURE__DYNAMIC_CAST:
            if self.extended_by is not None or self.extends is not None:
                source += "/* esxVI_%s_DynamicCast */\n" % self.name
                source += "ESX_VI__TEMPLATE__DYNAMIC_CAST(%s,\n" % self.name
                source += "{\n"

                source += self.generate_dynamic_cast_code()

                source += "})\n\n"
            else:
                report_error("cannot add dynamic cast support for an untyped object")

        # append to list
        if self.features & Object.FEATURE__LIST:
            source += "/* esxVI_%s_AppendToList */\n" % self.name
            source += "ESX_VI__TEMPLATE__LIST__APPEND(%s)\n\n" % self.name

        # deep copy
        if self.extended_by is None:
            if self.features & Object.FEATURE__DEEP_COPY:
                source += "/* esxVI_%s_DeepCopy */\n" % self.name
                source += "ESX_VI__TEMPLATE__DEEP_COPY(%s,\n" % self.name
                source += "{\n"

                source += self.generate_deep_copy_code()

                source += "})\n\n"

                if self.features & Object.FEATURE__LIST:
                    source += "/* esxVI_%s_DeepCopyList */\n" % self.name
                    source += "ESX_VI__TEMPLATE__LIST__DEEP_COPY(%s)\n\n" % self.name
        else:
            if self.features & Object.FEATURE__DEEP_COPY:
                source += "/* esxVI_%s_DeepCopy */\n" % self.name
                source += "ESX_VI__TEMPLATE__DYNAMIC_DEEP_COPY(%s)\n" % self.name
                source += "{\n"

                for extended_by in self.extended_by:
                    source += "    ESX_VI__TEMPLATE__DISPATCH__DEEP_COPY(%s)\n" % extended_by

                source += "},\n"
                source += "{\n"

                source += self.generate_deep_copy_code()

                source += "})\n\n"

                if self.features & Object.FEATURE__LIST:
                    source += "/* esxVI_%s_DeepCopyList */\n" % self.name
                    source += "ESX_VI__TEMPLATE__LIST__DEEP_COPY(%s)\n\n" % self.name

        # cast from any type
        if self.features & Object.FEATURE__ANY_TYPE:
            source += "/* esxVI_%s_CastFromAnyType */\n" % self.name
            source += "ESX_VI__TEMPLATE__CAST_FROM_ANY_TYPE(%s)\n" % self.name

            if self.features & Object.FEATURE__LIST:
                source += "/* esxVI_%s_CastListFromAnyType */\n" % self.name
                source += "ESX_VI__TEMPLATE__LIST__CAST_FROM_ANY_TYPE(%s)\n\n" % self.name

        # serialize
        if self.extended_by is None:
            if self.features & Object.FEATURE__SERIALIZE:
                source += "/* esxVI_%s_Serialize */\n" % self.name
                source += "ESX_VI__TEMPLATE__SERIALIZE(%s,\n" % self.name
                source += "{\n"

                source += self.generate_serialize_code()

                source += "})\n\n"

                if self.features & Object.FEATURE__LIST:
                    source += "/* esxVI_%s_SerializeList */\n" % self.name
                    source += "ESX_VI__TEMPLATE__LIST__SERIALIZE(%s)\n\n" % self.name
        else:
            if self.features & Object.FEATURE__SERIALIZE:
                source += "/* esxVI_%s_Serialize */\n" % self.name
                source += "ESX_VI__TEMPLATE__DYNAMIC_SERIALIZE(%s,\n" % self.name
                source += "{\n"

                for extended_by in self.extended_by:
                    source += "    ESX_VI__TEMPLATE__DISPATCH__SERIALIZE(%s)\n" % extended_by

                source += "},\n"
                source += "{\n"

                source += self.generate_serialize_code()

                source += "})\n\n"

                if self.features & Object.FEATURE__LIST:
                    source += "/* esxVI_%s_SerializeList */\n" % self.name
                    source += "ESX_VI__TEMPLATE__LIST__SERIALIZE(%s)\n\n" % self.name

        # deserilaize
        if self.features & Object.FEATURE__DESERIALIZE:
            source += "/* esxVI_%s_Deserialize */\n" % self.name
            source += "ESX_VI__TEMPLATE__DESERIALIZE(%s,\n" % self.name
            source += "{\n"

            source += self.generate_deserialize_code()

            source += "})\n\n"

            if self.features & Object.FEATURE__LIST:
                source += "/* esxVI_%s_DeserializeList */\n" % self.name
                source += "ESX_VI__TEMPLATE__LIST__DESERIALIZE(%s)\n\n" % self.name

        source += "\n\n"

        return source








class Enum:
    FEATURE__ANY_TYPE = (1 << 1)
    FEATURE__SERIALIZE = (1 << 2)
    FEATURE__DESERIALIZE = (1 << 3)


    def __init__(self, name, values, features = 0):
        self.name = name
        self.values = values
        self.features = features | Enum.FEATURE__SERIALIZE | Enum.FEATURE__DESERIALIZE

    def generate_typedef(self):
        return "typedef enum _esxVI_%s esxVI_%s;\n" % (self.name, self.name)

    def generate_typeenum(self):
        return "    esxVI_Type_%s,\n" % self.name

    def generate_typetostring(self):
        string = "          case esxVI_Type_%s:\n" % self.name
        string += "            return \"%s\";\n\n" % self.name

        return string

    def generate_typefromstring(self):
        string =  "           else if (STREQ(type, \"%s\")) {\n" % self.name
        string += "               return esxVI_Type_%s;\n" % self.name
        string += "           }\n"

        return string

    def generate_header(self):
        header = "/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *\n"
        header += " * VI Enum: %s\n" % self.name
        header += " */\n\n"

        # enum
        header += "enum _esxVI_%s {\n" % self.name
        header += "    esxVI_%s_Undefined = 0,\n" % self.name

        for value in self.values:
            header += "    esxVI_%s_%s,\n" % (self.name, capitalize_first(value))

        header += "};\n\n"

        # functions
        if self.features & Enum.FEATURE__ANY_TYPE:
            header += "int esxVI_%s_CastFromAnyType(esxVI_AnyType *anyType, esxVI_%s *item);\n" % (self.name, self.name)

        if self.features & Enum.FEATURE__SERIALIZE:
            header += "int esxVI_%s_Serialize(esxVI_%s item, const char *element, virBufferPtr output);\n" % (self.name, self.name)

        if self.features & Enum.FEATURE__DESERIALIZE:
            header += "int esxVI_%s_Deserialize(xmlNodePtr node, esxVI_%s *item);\n" % (self.name, self.name)

        header += "\n\n\n"

        return header

    def generate_source(self):
        source = "/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *\n"
        source += " * VI Enum: %s\n" % self.name
        source += " */\n\n"

        source += "static const esxVI_Enumeration _esxVI_%s_Enumeration = {\n" % self.name
        source += "    esxVI_Type_%s, {\n" % self.name

        for value in self.values:
            source += "        { \"%s\", esxVI_%s_%s },\n" % (value, self.name, capitalize_first(value))

        source += "        { NULL, -1 },\n"
        source += "    },\n"
        source += "};\n\n"

        # functions
        if self.features & Enum.FEATURE__ANY_TYPE:
            source += "/* esxVI_%s_CastFromAnyType */\n" % self.name
            source += "ESX_VI__TEMPLATE__ENUMERATION__CAST_FROM_ANY_TYPE(%s)\n\n" % self.name

        if self.features & Enum.FEATURE__SERIALIZE:
            source += "/* esxVI_%s_Serialize */\n" % self.name
            source += "ESX_VI__TEMPLATE__ENUMERATION__SERIALIZE(%s)\n\n" % self.name

        if self.features & Enum.FEATURE__DESERIALIZE:
            source += "/* esxVI_%s_Deserialize */\n" % self.name
            source += "ESX_VI__TEMPLATE__ENUMERATION__DESERIALIZE(%s)\n\n" % self.name

        source += "\n\n"

        return source





def report_error(message):
    print "error: " + message
    sys.exit(1)



def usage():
    print "%s <input-filename> <output-directory>" % sys.argv[0]
    sys.exit(0)



def capitalize_first(string):
    return string[:1].upper() + string[1:]



def parse_object(block):
    # expected format: object <name> [extends <name>]
    header_items = block[0][1].split()

    if len(header_items) < 2:
        report_error("line %d: invalid block header" % (number))

    assert header_items[0] == "object"

    name = header_items[1]
    extends = None

    if len(header_items) > 2:
        if header_items[2] != "extends":
            report_error("line %d: invalid block header" % (number))
        else:
            extends = header_items[3]

    properties = []

    for line in block[1:]:
        # expected format: <type> <name> <occurrence>
        items = line[1].split()

        if len(items) != 3:
            report_error("line %d: invalid property" % line[0])

        if items[2] not in Property.valid_occurrences:
            report_error("line %d: invalid occurrence" % line[0])

        properties.append(Property(type = items[0], name = items[1],
                                   occurrence = items[2]))

    return Object(name = name, extends = extends, properties = properties)



def parse_enum(block):
    # expected format: enum <name>
    header_items = block[0][1].split()

    if len(header_items) < 2:
        report_error("line %d: invalid block header" % (number))

    assert header_items[0] == "enum"

    name = header_items[1]

    values = []

    for line in block[1:]:
        # expected format: <value>
        values.append(line[1])

    return Enum(name = name, values = values)



def inherit_features(obj):
    if obj.extended_by is not None:
        for extended_by in obj.extended_by:
            objects_by_name[extended_by].features |= obj.features

    if obj.extends is not None:
        objects_by_name[obj.extends].features |= obj.features

    if obj.extended_by is not None:
        for extended_by in obj.extended_by:
            inherit_features(objects_by_name[extended_by])



def is_known_type(type):
    return type in predefined_objects or \
           type in predefined_enums or \
           type in objects_by_name or \
           type in enums_by_name



def open_and_print(filename):
    if filename.startswith("./"):
        print "  GEN    " + filename[2:]
    else:
        print "  GEN    " + filename

    return open(filename, "wb")










predefined_enums = ["Boolean"]

predefined_objects = ["AnyType",
                      "Int",
                      "Long",
                      "String",
                      "DateTime",
                      "ManagedObjectReference"]


additional_enum_features = { "ManagedEntityStatus"      : Enum.FEATURE__ANY_TYPE,
                             "TaskInfoState"            : Enum.FEATURE__ANY_TYPE,
                             "VirtualMachinePowerState" : Enum.FEATURE__ANY_TYPE }


additional_object_features = { "Event"                      : Object.FEATURE__LIST,
                               "HostCpuIdInfo"              : Object.FEATURE__ANY_TYPE | Object.FEATURE__LIST,
                               "ManagedObjectReference"     : Object.FEATURE__ANY_TYPE,
                               "ObjectContent"              : Object.FEATURE__DEEP_COPY | Object.FEATURE__LIST,
                               "PerfCounterInfo"            : Object.FEATURE__LIST,
                               "PerfEntityMetric"           : Object.FEATURE__LIST,
                               "PerfQuerySpec"              : Object.FEATURE__LIST,
                               "PerfMetricIntSeries"        : Object.FEATURE__DYNAMIC_CAST,
                               "PropertyFilterSpec"         : Object.FEATURE__LIST,
                               "ResourcePoolResourceUsage"  : Object.FEATURE__ANY_TYPE,
                               "SelectionSpec"              : Object.FEATURE__DYNAMIC_CAST,
                               "SharesInfo"                 : Object.FEATURE__ANY_TYPE,
                               "TaskInfo"                   : Object.FEATURE__ANY_TYPE | Object.FEATURE__LIST,
                               "UserSession"                : Object.FEATURE__ANY_TYPE,
                               "VirtualMachineQuestionInfo" : Object.FEATURE__ANY_TYPE }


removed_object_features = { "DynamicProperty"          : Object.FEATURE__SERIALIZE,
                            "ObjectContent"            : Object.FEATURE__SERIALIZE,
                            "ObjectUpdate"             : Object.FEATURE__SERIALIZE,
                            "PropertyChange"           : Object.FEATURE__SERIALIZE,
                            "PropertyFilterUpdate"     : Object.FEATURE__SERIALIZE,
                            "TaskInfo"                 : Object.FEATURE__SERIALIZE,
                            "UpdateSet"                : Object.FEATURE__SERIALIZE,
                            "VirtualMachineConfigInfo" : Object.FEATURE__SERIALIZE }




if "srcdir" in os.environ:
    input_filename = os.path.join(os.environ["srcdir"], "esx/esx_vi_generator.input")
    output_dirname = os.path.join(os.environ["srcdir"], "esx")
else:
    input_filename = os.path.join(os.getcwd(), "esx_vi_generator.input")
    output_dirname = os.getcwd()



typedef = open_and_print(os.path.join(output_dirname, "esx_vi_types.generated.typedef"))
typeenum = open_and_print(os.path.join(output_dirname, "esx_vi_types.generated.typeenum"))
typetostring = open_and_print(os.path.join(output_dirname, "esx_vi_types.generated.typetostring"))
typefromstring = open_and_print(os.path.join(output_dirname, "esx_vi_types.generated.typefromstring"))
header = open_and_print(os.path.join(output_dirname, "esx_vi_types.generated.h"))
source = open_and_print(os.path.join(output_dirname, "esx_vi_types.generated.c"))



number = 0
objects_by_name = {}
enums_by_name = {}
block = None



for line in file(input_filename, "rb").readlines():
    number += 1

    if "#" in line:
        line = line[:line.index("#")]

    line = line.lstrip().rstrip()

    if len(line) < 1:
        continue

    if line.startswith("object") or line.startswith("enum"):
        if block is not None:
            report_error("line %d: nested block found" % (number))
        else:
            block = []

    if block is not None:
        if line == "end":
            if block[0][1].startswith("object"):
                obj = parse_object(block)
                objects_by_name[obj.name] = obj
            else:
                enum = parse_enum(block)
                enums_by_name[enum.name] = enum

            block = None
        else:
            block.append((number, line))



for enum in enums_by_name.values():
    # apply additional features
    if enum.name in additional_enum_features:
        enum.features |= additional_enum_features[enum.name]



for obj in objects_by_name.values():
    for property in obj.properties:
        if property.occurrence != Property.OCCURRENCE__IGNORED and \
           not is_known_type(property.type):
            report_error("object '%s' contains unknown property type '%s'" % (obj.name, property.type))

    if obj.extends is not None:
        if not is_known_type(obj.extends):
            report_error("object '%s' extends unknown object '%s'" % (obj.name, obj.extends))

    # detect list usage
    for property in obj.properties:
        if (property.occurrence == Property.OCCURRENCE__REQUIRED_LIST or \
            property.occurrence == Property.OCCURRENCE__OPTIONAL_LIST) and \
           property.type not in predefined_objects:
            objects_by_name[property.type].features |= Object.FEATURE__LIST

    # apply/remove additional features
    if obj.name in additional_object_features:
        obj.features |= additional_object_features[obj.name]

    if obj.name in removed_object_features:
        obj.features &= ~removed_object_features[obj.name]

    # spread deep copy onto properties
    if obj.features & Object.FEATURE__DEEP_COPY:
        for property in obj.properties:
            if property.occurrence != Property.OCCURRENCE__IGNORED and \
               property.type not in predefined_objects:
                objects_by_name[property.type].features |= Object.FEATURE__DEEP_COPY

    # detect extended_by relation
    if obj.extends is not None:
        extended_obj = objects_by_name[obj.extends]

        if extended_obj.extended_by is None:
            extended_obj.extended_by = [obj.name]
        else:
            extended_obj.extended_by.append(obj.name)





for obj in objects_by_name.values():
    inherit_features(obj)





typedef.write("/* Generated by esx_vi_generator.py */\n\n\n\n")
typeenum.write("/* Generated by esx_vi_generator.py */\n\n")
typetostring.write("/* Generated by esx_vi_generator.py */\n\n")
typefromstring.write("/* Generated by esx_vi_generator.py */\n\n")
header.write("/* Generated by esx_vi_generator.py */\n\n\n\n")
source.write("/* Generated by esx_vi_generator.py */\n\n\n\n")


typedef.write("/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *\n" +
              " * VI Enums\n" +
              " */\n\n")



names = enums_by_name.keys()
names.sort()


for name in names:
    typedef.write(enums_by_name[name].generate_typedef())
    typeenum.write(enums_by_name[name].generate_typeenum())
    typetostring.write(enums_by_name[name].generate_typetostring())
    typefromstring.write(enums_by_name[name].generate_typefromstring())
    header.write(enums_by_name[name].generate_header())
    source.write(enums_by_name[name].generate_source())



typedef.write("\n\n\n" +
              "/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *\n" +
              " * VI Types\n" +
              " */\n\n")

typeenum.write("\n")

typetostring.write("\n")

typefromstring.write("\n")



names = objects_by_name.keys()
names.sort()


for name in names:
    typedef.write(objects_by_name[name].generate_typedef())
    typeenum.write(objects_by_name[name].generate_typeenum())
    typetostring.write(objects_by_name[name].generate_typetostring())
    typefromstring.write(objects_by_name[name].generate_typefromstring())
    header.write(objects_by_name[name].generate_header())
    source.write(objects_by_name[name].generate_source())