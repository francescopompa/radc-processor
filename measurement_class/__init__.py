"""
Class representing a single - or a suite of - measurements.
"""
import os
import time


#
# Todo: replace point_number with suffix of variable length
# Todo: fix setting new id on increment
#
class Measurement():

    base_path = "C:/Users/utrfh/WS22-23 (MA) Masterarbeit/Measurements/"

    key_defaults = {
        # "group" has no default as it has to be set explicitely.
        "date": time.strftime("%y%m%d"),
        "subgroup": "a",
        "measurement_number": "01",
        "attempt_number": "1",
        "group_desc": "",
        "subgroup_desc": "",
        "suffixes": [],
    }

    _validation_functions = {
        # "id": ,
        "group": lambda x: x.isalpha() and x.isupper() and len(x)==2 and x.isascii(),
        "date": lambda x: x.isdigit() and len(x) == 6 and time.strptime(x, "%y%m%d"),
        "subgroup": lambda x: x.isalpha() and x.islower() and len(x)==1 and x.isascii(),
        "measurement_number": lambda x: x.isdigit() and len(x)==2,
        "attempt_number": lambda x: x.isdigit() and len(x)==1,
        "group_desc": lambda x: x is None or x.isascii(),
        "subgroup_desc": lambda x: x is None or x.isascii(),
        # "point_number": lambda x: (x is None) or (x.isdigit() and len(x)>=1),
        "suffixes": lambda x: all([i.isascii() for i in x])
    }

    def __init__(
        self,
        id: str = None,
        group=None,
        date=None,
        subgroup=None,
        measurement_number = None, # "01"
        attempt_number = None, # "1"
        group_desc = None, # ""
        subgroup_desc = None, # ""
        suffixes = None,
        ) -> None:

        self.group = group
        self.date = date
        self.subgroup = subgroup
        self.measurement_number = measurement_number
        self.attempt_number = attempt_number
        self.group_desc = group_desc
        self.subgroup_desc = subgroup_desc
        self.suffixes = suffixes

        if id is not None:
            self._init_with_id(id)

        self._validate_keys()

    def _update_property(self, propname, value=None): #, default=None):
        default = (
            None if propname not in self.key_defaults
            else self.key_defaults[propname]
            )


    def _update_property(self, propname, value=None, default=None):
        prop = getattr(self, propname)
        setattr(self,
                propname,
                (   prop if prop is not None
                    else value if value is not None and value != ""
                    else default
                )
        )

    def _init_with_id(self, id):
        spl = id.split("_")
        fullgroup = spl[0]
        suffixes = spl[2:]

        date = None
        if len(fullgroup) >= 8:
            date = fullgroup[2:8]

        mnum = None
        anum = None
        if len(spl) > 1:
            numbers = spl[1]
            if "-" in numbers:
                mnum = numbers.split("-")[0]
                anum = numbers.split("-")[1]

        self._update_property("group", fullgroup[0:2])
        self._update_property("date", date)
        self._update_property("subgroup", fullgroup[8:])

        self._update_property("measurement_number", mnum)
        self._update_property("attempt_number", anum)

        self._update_property("group_desc")
        self._update_property("subgroup_desc")

        self._update_property("suffixes", suffixes)

    def _reset_children(self, key):
        keys = ["group", "date", "subgroup", "measurement_number", "attempt_number"]
        start = keys.index(key) if key in keys else len(keys)

        for key in keys[start+1:]:
            setattr(self, key, self.key_defaults[key])

    def _validate_keys(self):
        for key, func in self._validation_functions.items():
            val = getattr(self, key)
            # print(key, val)
            if not func(val):
                raise ValueError(
                    f"Wrong value for {key}: {val}"
                    )

    @property
    def id(self):
        return "_".join(
            [
                f"{self.group}{self.date}{self.subgroup}",
                f"{self.measurement_number}-{self.attempt_number}",
            ] + self.suffixes
        )


    @property
    def path(self, key=None):
        group_path = os.path.join(
            self.base_path, f"{self.group} - {self.group_desc}"
        )
        subgroup_path = os.path.join(
           group_path, f"{self.date}{self.subgroup} {self.subgroup_desc}"
        )
        return group_path, subgroup_path

    @property
    def groupid(self):
        return self.id.split('_')[0]


    def _increment_number(self, numberstr):
        return f"{int(numberstr)+1:0{len(numberstr)}}"

    def _increment_letter_old(self, letterchar):
        overflow = False
        new_ord = ord(letterchar)+1
        a = 97
        z = 122
        A = 65
        Z = 90
        if letterchar.islower() and new_ord > z:
            new_ord = a # reset this position
            overflow = True
        elif letterchar.isupper() and new_ord > Z:
            new_ord = A # reset this position
            overflow = True

        return f"{chr(new_ord)}", overflow

    def _increment_letter(self, letters, idx=-1):
        overflow = False
        letterchar = letters[idx]
        new_ord = ord(letterchar)+1
        a = 97
        z = 122
        A = 65
        Z = 90
        if letterchar.islower() and new_ord > z:
            new_ord = a # reset this position
            overflow = True
        elif letterchar.isupper() and new_ord > Z:
            new_ord = A # reset this position
            overflow = True
        # Assuming idx is always negative.
        new_letters = letters[0:idx]+chr(new_ord)+letters[len(letters)+idx+1:]
        if overflow is True:
            if abs(idx-1) > len(letters):
                raise ValueError(f"Reached end of letters from {letters} to {new_letters}")
            new_letters = self._increment_letter(new_letters, idx-1)
        return new_letters

    def increment(self, key, val=None, desc=None, subdesc=None, idx=0):
        if key in ["meas", "measurement"]:
            key = "measurement_number"
        elif key in ["att", "attempt"]:
            key = "attempt_number"
        elif key == "suffix":
            key = "suffixes"

        match key:
            case "group":
                self.group = self._increment_letter(self.group)
                if desc is not None:
                        self.group_desc = desc
                if subdesc is not None:
                        self.subgroup_desc = subdesc

            case "subgroup":
                self.subgroup = self._increment_letter(self.subgroup)

                if desc is not None or subdesc is not None:
                    self.subgroup_desc = desc if desc is not None else subdesc

            case "measurement_number":
                self.measurement_number = self._increment_number(self.measurement_number)
            case "attempt_number":
                self.attempt_number = self._increment_number(self.attempt_number)
            case "suffixes":
                if val is None:
                    try:
                        val = self._increment_number(self.suffixes[idx])
                    except ValueError:
                        val = self._increment_letter(self.suffixes[idx])
                self.suffixes[idx] = str(val)
            case _:
                raise ValueError(f"Key unknown: {key}")

        self._reset_children(key)
        self._validate_keys()
        print("New id:", self.id)