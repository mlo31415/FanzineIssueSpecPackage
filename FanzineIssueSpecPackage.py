# A FanzineIssueSpec contains the information for one fanzine issue's specification, e.g.:
#  V1#2, #3, #2a, Dec 1967, etc.
# It can be a volume+number or a whole numer or a date. (It can be more than one of these, also, and all are retained.)

from HelpersPackage import ToNumeric

class FanzineIssueSpec:

    def __init__(self, Vol=None, Num=None, NumSuffix=None, Whole=None, WSuffix=None, Year=None, Month=None, MonthText=None, Day=None, DayText=None):
        self._Vol=ToNumeric(Vol)
        self._Num=ToNumeric(Num)
        self._NumSuffix=NumSuffix       # For things like issue '17a'
        self._Whole=ToNumeric(Whole)
        self._WSuffix=WSuffix
        self._Year=ToNumeric(Year)
        self._Month=ToNumeric(Month)
        self._MonthText=MonthText       # In case the month is specified using something other than a month name, we save the special text here
        self._Day=ToNumeric(Day)
        self._DayText=DayText           # In case the day is specified using something other than a numer (E.g., "Christmas Day"), we save the special text here
        self._UninterpretableText=None   # Ok, I give up.  Just hold the text as text.
        self._TrailingGarbage=None       # The uninterpretable stuff following the interpretable spec held in this instance

    def CaseInsensitiveCompare(self, s1: str, s2: str):
        if s1 == s2:
            return True
        if s1 is None or s2 is None:
            return False    # We already know that s1 and s2 are different
        return s1.lower() == s2.lower() # Now that we know that neither is None, we can do the lower case compare

    # Are the Num fields equal?
    # Both could be None; otherwise both must be equal
    def __NumEq__(self, other):
        return self._Num == other._Num and self.CaseInsensitiveCompare(self._NumSuffix, other._NumSuffix)

    def __VolEq__(self, other):
        return self._Vol == other._Vol

    def __WEq__(self, other):
        return self._Whole == other._Whole and self.CaseInsensitiveCompare(self._WSuffix, other._WSuffix)

    def __VNEq__(self, other):
        return self.__VolEq__(other) and self.__NumEq__(other)

    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)
    def __IssueEQ__(self, other):
        if self.__VNEq__(other) and self.__WEq__(other):
            return True
        if (self._Whole is None or other._Whole is None) and self.__VNEq__(other):
            return True
        if (self._Num is None or self._Vol is None or other._Num is None or other._Vol is None) and self.__WEq__(other):
            return True
        return False

    def __DateEq__(self, other):
        # If we're checking against a null input, it's not equal
        if other is None:
            return False
        # If either date is entirely None, its not equal
        if self._Year is None and self._Month is None and self._Day is None:
            return None
        if other._Year is None and other._Month is None and other._Day is None:
            return None
        # OK, we know that both self and other have a non-None date element, so just check for equality
        return self._Year == other._Year and self._Month == other._Month and self._Day == other._Day

    # Class equality check.
    def __eq__(self, other):
        # If we're checking against a null input, it's not equal
        if other is None:
            return False
        # If the issue numbers exist and match, it's equal even if other stuff doesn't match
        if self.__IssueEQ__(other):
            return True
        # All that's left that might match is the date
        # Note that we ignore MonthText and DayText for purposes of checking equality
        return self.__DateEq__(other)


    def __ne__(self, other):
        return not self.__eq__(other)

    def Copy(self, other):
        self._Vol=other.Vol
        self._Num=other.Num
        self._NumSuffix=other.NumSuffix
        self._Whole=other.Whole
        self._WSuffix=other.WSuffix
        self._Year=other.Year
        self._Month=other.Month
        self._MonthText=other.MonthText
        self._Day=other.Day
        self._DayText=other.DayText
        self._UninterpretableText=other.UninterpretableText
        self._TrailingGarbage=other.TrailingGarbage

    # .....................
    @property
    def Vol(self):
        return self._Vol

    @Vol.setter
    def Vol(self, val):
        self._Vol=ToNumeric(val)

    @Vol.getter
    def Vol(self):
        return self._Vol

    # .....................
    @property
    def Num(self):
        return self._Num

    @Num.setter
    def Num(self, val):
        self._Num=ToNumeric(val)

    @Num.getter
    def Num(self):
        return self._Num

    # .....................
    @property
    def NumSuffix(self):
        return self._NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val):
        self._NumSuffix=val

    @NumSuffix.getter
    def NumSuffix(self):
        return self._NumSuffix

    #.....................
    @property
    def Whole(self):
        return self._Whole

    @Whole.setter
    def Whole(self, val):
        self._Whole=ToNumeric(val)

    @Whole.getter
    def Whole(self):
        return self._Whole

    # .....................
    @property
    def WSuffix(self):
        return self._WSuffix

    @WSuffix.setter
    def WSuffix(self, val):
        self._WSuffix=val

    @WSuffix.getter
    def WSuffix(self):
        return self._WSuffix

    #.....................
    @property
    def Year(self):
        return self._Year

    @Year.setter
    def Year(self, val):
        self._Year=ToNumeric(val)

    @Year.getter
    def Year(self):
        return self._Year

    #.....................
    @property
    def Month(self):
        return self._Month

    @Month.setter
    def Month(self, val):
        self._Month=ToNumeric(val)
        self._MonthText=None    # If we set a numeric month, any text month gets blown away as no longer relevant

    @Month.getter
    def Month(self):
        return self._Month

    #.....................
    @property
    def MonthText(self):
        return self._MonthText

    @MonthText.setter
    def MonthText(self, val):
        self._MonthText=val
        #TODO: Compute the real month and save it in _Month

    @MonthText.getter
    def MonthText(self):
        return self._MonthText

    #.....................
    @property
    def Day(self):
        return self._Day

    @Day.setter
    def Day(self, val):
        self._Day=ToNumeric(val)
        self._DayText=None   # If we set a numeric month, any text month gets blown away as no longer relevant

    @Day.getter
    def Day(self):
        return self._Day

    # .....................
    @property
    def DayText(self):
        return self._DayText

    @DayText.setter
    def DayText(self, val):
        self._DayText=val
        #TODO: Compute the real day and save it in _Day

    @DayText.getter
    def DayText(self):
        return self._DayText

    #.....................
    @property
    def UninterpretableText(self):
        return self._UninterpretableText

    @UninterpretableText.setter
    def UninterpretableText(self, val):
        if val is None:
            self._UninterpretableText=None
            return
        val=val.strip()
        if len(val) == 0:
            self._UninterpretableText=None
            return
        self._UninterpretableText=val

    @UninterpretableText.getter
    def UninterpretableText(self):
        return self._UninterpretableText

    #.....................
    @property
    def TrailingGarbage(self):
        return self._TrailingGarbage

    @TrailingGarbage.setter
    def TrailingGarbage(self, val):
        if val is None:
            self._TrailingGarbage=None
            return
        val=val.strip()
        if len(val) == 0:
            self._TrailingGarbage=None
            return
        self._TrailingGarbage=val

    @TrailingGarbage.getter
    def TrailingGarbage(self):
        return self._TrailingGarbage

    # .....................
    def SetWhole(self, num: int, suffix: str):
        self.Whole=num
        if suffix is None:
            return self
        if len(suffix) == 1 and suffix.isalpha():  # E.g., 7a
            self.WSuffix=suffix
        elif len(suffix) == 2 and suffix[0] == '.' and suffix[1].isnumeric():  # E.g., 7.1
            self.WSuffix=suffix
        else:
            self.TrailingGarbage=suffix
        return self

    # .....................
    def SetDate(self, y, m):
        self.Year=ToNumeric(y)
        self.Month=ToNumeric(m)
        return self

    #.......................
    # Convert the FanzineIssueSpec into a debugging form
    def DebugStr(self):
        if self.UninterpretableText is not None:
            return "IS("+self.UninterpretableText+")"

        v="-"
        if self.Vol is not None:
            v=str(self.Vol)
        n="-"
        if self.Num is not None:
            n=str(self.Num)
            if self.NumSuffix is not None:
                n=n+str(self.NumSuffix)
        w="-"
        if self.Whole is not None:
            w=str(self.Whole)
            if self.WSuffix is not None:
                n=n+str(self.WSuffix)
        d=""
        if self.Year is not None:
            d=str(self.Year)
        if self.Month is not None:
            d=d+":"+str(self.Month)
        if self.MonthText is not None:
            d=d+":"+self.MonthText()
        if self.Day is not None:
            d=d+"::"+str(self.Day)
        if self.DayText is not None:
            d=d+"::"+self.DayText()
        if d == "":
            d="-"

        s="IS(V"+v+", N"+n+", W"+w+", D"+d
        if self.TrailingGarbage is not None:
            s=s+", TG='"+self.TrailingGarbage+"'"
        if self.UninterpretableText is not None:
            s=s+", UT='"+self.UninterpretableText+"'"
        s=s+")"

        return s

    #.......................
    def IsEmpty(self):
        return self._Whole is None and self._Num is None and self._WSuffix is None and self._NumSuffix is None and self._Month is None and self._MonthText is None \
            and self._Day is None and self._DayText is None and self._UninterpretableText and self._TrailingGarbage is None and self._Vol is None and self._Year is None

    #.......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self):
        if self.UninterpretableText is not None:
            return self.UninterpretableText

        tg=""
        if self.TrailingGarbage is not None:
            tg=" "+self.TrailingGarbage

        if self.Vol is not None and self.Num is not None and self.Whole is not None:
            s="V"+str(self.Vol)+"#"+str(self.Num)
            if self.NumSuffix is not None:
                s+=str(self.NumSuffix)
            s+=" (#"+str(self.Whole)
            if self.WSuffix is not None:
                s+=str(self.WSuffix)
            s+=")"
            return s+tg

        if self.Vol is not None and self.Num is not None:
            s="V"+str(self.Vol)+"#"+str(self.Num)
            if self.NumSuffix is not None:
                s+=str(self.NumSuffix)
            return s+tg

        if self.Whole is not None:
            s="#"+str(self.Whole)
            if self.WSuffix is not None:
                s+=str(self.WSuffix)
            return s+tg

        # We don't treat a day without a month and year or a month without a year as valid and printable
        if self.Year is not None:
            if self.Month is None:
                return str(self.Year)+" "+tg
            if self._MonthText is not None:
                return self._MonthText+" "+str(self._Year)+" "+tg  # There's never a monthtext+day combination
            if self._DayText is not None:
                return self._DayText+ " "+str(self._Year)+" "+tg
            return str(self._Day)+ " "+str(self._Month)+" "+str(self._Year)+" "+tg
                #TODO: Conver to 3-character month

        return tg



#################################################################################
#################################################################################
# Now define FanzineIssueSpecList
#################################################################################
#################################################################################
# A Fanzine issue spec list contains the information to handle a list of issues of a single fanzine.
# It includes the series name, editors(s), and a list of Fanzine Issue specs.
#TODO: This can be profitably extended by changing the ISL class to include specific names and editors for each issue, since sometimes
#TODO: a series does not have a consistent set throughout.

class FanzineIssueSpecList:
    def __init__(self, List=None):
        self.List=List  # Use setter

    def AppendIS(self, fanzineIssueSpec):
        if isinstance(fanzineIssueSpec, FanzineIssueSpec):
            self._list.append(fanzineIssueSpec)
        elif isinstance(fanzineIssueSpec, FanzineIssueSpecList):
            self._list.extend(fanzineIssueSpec.List)
        elif fanzineIssueSpec is None:
            return
        else:
            print("****FanzineIssueSpecList.AppendIS() had strange input")
        return self

    def Extend(self, isl):
        self._list.extend(isl)
        return self

    def DebugStr(self):
        s=""
        for i in self._list:
            if len(s) > 0:
                s=s+",  "
            if i is not None:
                s=s+i.DebugStr()
            else:
                s=s+"Missing ISList"
        if len(s) == 0:
            s="Empty ISlist"
        return s

    def __str__(self):   # Format the ISL for pretty
        s=""
        for i in self._list:
            if i is not None:
                if len(s) > 0:
                    s=s+", "
                s=s+str(i)
        return s

    def __len__(self):
        return len(self._list)

    @property
    def List(self):
        return self._list

    @List.setter
    def List(self, val):
        if val is None:
            self._list=[]
            return
        if isinstance(val, FanzineIssueSpec):
            self._list=[val]
            return
        if isinstance(val, FanzineIssueSpecList):
            self._list=val.List
        print("****FanzineIssueSpecList.List setter() had strange input")

    @List.getter
    def List(self):
        return self._list

    def __getitem__(self, key):
        return self._list[key]

    def __setitem__(self, key, value):
        self._list[key]=value
        return self
