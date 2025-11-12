# This package of classes provides support for naming and listing fanzines.
# It consists of five classes
#   FanzineSerial           -- contains a single serial number (V4#3, #22, #7A, VII, etc)
#   FanzineDate             -- contains a date (June, 1949; 2005; 2/22/79; etc)
#   FanzineIssueSpec        -- contains a FanzineDate and a FanzineSerial providing a complete sequence designation for an issue
#                              it contains no other information about the issue such as name or series
#   FanzineIssueSpecList    -- contains a list of FanzineIssueSpecs all relevant to a single fanzine
#                              It differs  from a FanzineSeriesList in that it contains a list of FanzineIssueSpecs and not a list of FanzineIssueInfos
#   FanzineIssueInfo        -- contains information for a single issue (title, editor, sequence, etc). Includes a FanzineIssueSpec
#   FanzineSeriesList       -- contains information for a fanzine series (Locus, VOID, File 770, Axe, etc). Includes a list of FanzineIssueInfos

# A FanzineIssueSpec contains the information for one fanzine issue's specification, e.g.:
#  V1#2, #3, #2a, Dec 1967, etc.
# It can be a volume+number or a whole number or a date. (It can be more than one of these, also, and all are retained.)

# The top level is a FanzineIssueSpecList which holds many FanzineIssueSpecs
# A FanzineIssueSpec holds the serial number and date for a single issue
#     It also holds a FanzineSerial and a FanzineDate which hold, respectively, the issue designation and the issue date
#     (This would also be the right place to put other issue-specific information such as editor, pagecount, etc.)
#     (It probably should be merged with the FanzineIssueData class of 1943FanzineList)
from __future__ import annotations

from typing import Self
import re
from contextlib import suppress
from datetime import datetime

from Locale import Locale
from FanzineDateTime import FanzineDate, MonthNameToInt

from Log import Log
from HelpersPackage import ToNumeric, IsInt
from HelpersPackage import MergeURLs
from HelpersPackage import Pluralize
from HelpersPackage import InterpretRoman
from HelpersPackage import CaseInsensitiveCompare
from HelpersPackage import ParmDict

class FanzineCounts:
    def __init__(self, Titlecount: int=0, Issuecount: int=0, Pagecount: int=0, Pdfcount: int=0, Pdfpagecount: int=0, Title: str=None, Titlelist: set[str]=None):

        if Titlelist is None:
            self.Titlelist: set=set()       # A set to hold title names.  This is needed to count titles when fanzines are not ordered in title order
        else:
            self.Titlelist=Titlelist
        if Title:
            self.Titlelist.add(Title)
        self.Titlecount: int=Titlecount  # Count of distinct titles.
        self.Issuecount: int=Issuecount  # Count of issues in all the titles
        self.Pagecount: int=Pagecount   # Cumulative page count for all the issues
        self.Pdfcount: int=Pdfcount     # Count of issues which are PDFs
        self.Pdfpagecount: int=Pdfpagecount
        if self.Issuecount == 0 and self.Pagecount > 0:   # If it is initialized with a pagecount only, add an issue count of 1
            self.Issuecount=1

    # .....................
    def __str__(self) -> str:  # FanzineCounts
        s=""
        t=self.Titlecount
        if t == 0 and len(self.Titlelist) > 0:
            t=len(self.Titlelist)
        i=self.Issuecount
        p=self.Pagecount
        if t > 0:
            s+=Pluralize(t, "title", Spacechar="&nbsp;")+", "
        if i > 0:
            s+=Pluralize(i, "issue", Spacechar="&nbsp;")+", "
            s+=Pluralize(p, "page", Spacechar="&nbsp;")
        return s

    # .....................
    def __add__(self, b: FanzineCounts | FanzineIssueInfo | int | str) -> FanzineCounts:  # FanzineCounts
        # Note that titlecount, pdfcount and pdfpagecount need to be incremented (or not) independently
        if isinstance(b, FanzineCounts):
            return FanzineCounts(Issuecount=self.Issuecount+b.Issuecount, Pagecount=self.Pagecount+b.Pagecount, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)
        elif isinstance(b, FanzineIssueInfo):
            return FanzineCounts(Issuecount=self.Issuecount+1, Pagecount=self.Pagecount+b.Pagecount, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)
        elif isinstance(b, int):
            # The int is taken to be a pagecount, and the issue count is automatically incremented
            return FanzineCounts(Issuecount=self.Issuecount+1, Pagecount=self.Pagecount+b, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)
        elif isinstance(b, str):
            return FanzineCounts(Issuecount=self.Issuecount, Pagecount=self.Pagecount, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)

        assert False

    #......................
    # Needed for += for mutable objects
    def __iadd__(self, b: FanzineCounts | FanzineIssueInfo | int | str) -> FanzineCounts:  # FanzineCounts
        # Note that titlecount, pdfcount and pdfpagecount need to be incremented (or not) independently
        if isinstance(b, FanzineCounts):
            self.Issuecount+=b.Issuecount
            self.Pagecount+=b.Pagecount
            return self
        elif isinstance(b, FanzineIssueInfo):
            self.Issuecount+=1
            self.Pagecount+=b.Pagecount
            return self
        elif isinstance(b, int):
            # The int is taken to be a pagecount, and the issue count is automatically incremented
            self.Issuecount+=1
            self.Pagecount+=b
            return self
        elif isinstance(b, str):
            self.Titlelist.add(b)
            return self

        assert False

    # -------------------------------------------------------------------------
    # Compute a counts annotation from a 2-tuple element -- used in calls to WriteTable
    def Annotate(self, special: int=0) -> str:
        s=self.__str__()
        if s and special != 1:
            s="("+s+")"
        return s


############################################################################################
# A class holding information about a fanzine series
# Note that for onesies or some types we sometimes create an artificial  fanzine series to go with a single issues
class FanzineSeriesInfo:

    def __init__(self, SeriesName: str = "", DisplayName: str = "", DirURL: str = "", Issuecount: int=0,
                 Pagecount: int = 0, Editor: str = "", Country: str = "", AlphabetizeIndividually: bool=False, Keywords: ParmDict=None) -> None:
        _SeriesName: str=""  # Name of the fanzine series of which this is an issue
        _DisplayName: str=""  # Name to use for this issue. Includes issue serial and or date
        _DirURL: str=""  # URL of series directory
        _Counts: FanzineCounts  # Page and IssueName count for all the issues fanac has for this series
        _Editor: str=""  # The editor for this series (if there was one for essentially all issues)
        _Country: str="" # The country for this issue (gotten from the series's country
        _AlphabetizeIndividually: bool=False
        _Keywords: ParmDict=ParmDict()  # A list of keywords

        # Use the properties to set the values for all of the instance variables. We do this so that any special setter processing is done with the init values.
        self.SeriesName=SeriesName
        self.DisplayName=DisplayName
        self.DirURL=DirURL
        self.Counts=FanzineCounts(Issuecount=Issuecount, Pagecount=Pagecount)
        self.Editor=Editor
        self.Country=Country
        self.AlphabetizeIndividually=AlphabetizeIndividually
        if Keywords is None:
            Keywords=ParmDict()
        self._Keywords=Keywords
        pass

    # .....................
    def __str__(self) -> str:
        out=""
        if self.DisplayName != "":
            return self.DisplayName
        elif self.SeriesName != "":
            out=self.SeriesName

        return out.strip()

    # .....................
    def __repr__(self) -> str:
        out=""
        if self.DisplayName != "":
            out="'"+self.DisplayName+"'"
        elif self.SeriesName != "":
            out=self.SeriesName

        if self.Editor != "":
            out+=f"  ed:{self.Editor}"
        if self.Issuecount > 0:
            out+=f"  {self.Issuecount} issues"
        if self.Pagecount > 0:
            out+=f"  {self.Pagecount} pp"
        if self.Country != "":
            out+=f"   ({self.Country})"
        return out.strip()

    # -----------------------------
    # Note that this ignores quite a lot in creating the hash value
    # Be careful!
    def __hash__(self):
        #TODO This appears to be unused.  Should it be expanded to match the class members or dropped?
        return hash(self._SeriesName)+hash(self._Editor)+hash(self._Country)

    # .....................
    # Note that page and issue count are not included in equality comparisons.
    # This allows for accumulation of those numbers while retaining series identity
    def __eq__(self, other: FanzineSeriesInfo) -> bool:
        if other is None:
            return False

        if self._SeriesName != other._SeriesName:
            return False
        if self._Editor != other._Editor:
            return False
        if self._Country != other._Country:
            return False

        return True

    # .....................
    # When we add, we add to the counts
    def __add__(self, b: Self|FanzineIssueInfo|int):
        ret=FanzineSeriesInfo(SeriesName=self.SeriesName, Editor=self.Editor, DisplayName=self.DisplayName, Country=self.Country, DirURL=self.DirURL)
        #Log("FanzineSeriesInfo.add:  self.URL="+self.URL+"     b.URL="+b.URL)
        if isinstance(b, FanzineSeriesInfo):
            ret.Issuecount=self.Issuecount+b.Issuecount
            ret.Pagecount=self.Pagecount+b.Pagecount
        elif isinstance(b, FanzineIssueInfo):
            ret.Issuecount=self.Issuecount+1
            ret.Pagecount=self.Pagecount+b.Pagecount
        else:
            assert isinstance(b, int)
            ret.Issuecount=self.Issuecount+1
            ret.Pagecount=self.Pagecount+b
        return ret

    # .....................
    # When we add, we add to the counts
    # Note that this is an in-paces add to aupport += for mutable objects
    def __iadd__(self, b: Self|FanzineIssueInfo|int):
        if isinstance(b, FanzineSeriesInfo):
            self.Issuecount+=b.Issuecount
            self.Pagecount+=b.Pagecount
        elif isinstance(b, FanzineIssueInfo):
            self.Issuecount+=1
            self.Pagecount+=b.Pagecount
        else:
            assert isinstance(b, int)
            self.Issuecount+=1
            self.Pagecount+=b
        return self

    # .....................
    def Deepcopy(self) -> FanzineSeriesInfo:
        new=FanzineSeriesInfo()
        new.SeriesName=self.SeriesName
        new.DisplayName=self.DisplayName
        new.DirURL=self.DirURL
        new.Pagecount=self.Pagecount
        new.Issuecount=self.Issuecount
        new.Editor=self.Editor
        new.Country=self.Country
        #new.FanzineSeriesInfo=self.FanzineSeriesInfo
        return new

    # .....................
    def IsEmpty(self) -> bool:
        if self.SeriesName != "":
            return False
        if self._DisplayName != "":
            return False
        if self.DirURL != "":
            return False
        if self.Editor != "":
            return False
        if str(self.Country) != "":
            return False
        
        return True

    # .....................
    # Generate a proper URL for the item
    @property
    def URL(self) -> str:

        if self.DirURL == "":
            return "<no url>"

        return MergeURLs(self.DirURL, self.DirURL)

    # .....................
    @property
    def SeriesName(self) -> str:
        return self._SeriesName
    @SeriesName.setter
    def SeriesName(self, val: str) -> None:
        self._SeriesName=val.strip()

    # .....................
    @property
    def DisplayName(self) -> str:
        if self._DisplayName != "":
            return self._DisplayName
        return self.SeriesName
    @DisplayName.setter
    def DisplayName(self, val: str) -> None:
        self._DisplayName=val.strip()

    # .....................
    @property
    def DirURL(self) -> str:
        return self._URL
    @DirURL.setter
    def DirURL(self, val: str) -> None:
        self._URL=val

    # .....................
    @property
    def Counts(self) -> FanzineCounts:
        return self._Counts
    @Counts.setter
    def Counts(self, val: FanzineCounts) -> None:
        self._Counts=val

    # .....................
    @property
    def Pagecount(self) -> int:
        return self._Counts.Pagecount
    @Pagecount.setter
    def Pagecount(self, val: int) -> None:
        self._Counts.Pagecount=val
        
    # .....................
    @property
    def Issuecount(self) -> int:
        return self._Counts.Issuecount
    @Issuecount.setter
    def Issuecount(self, val: int) -> None:
        self._Counts.Issuecount=val

    # .....................
    # Needed for compatibility, but always zero
    @property
    def Titlecount(self) -> int:
        return self._Counts.Titlecount

    # .....................
    @property
    def Country(self) -> str:
        return self._Country
    @Country.setter
    def Country(self, val: str) -> None:
        self._Country=val
        
    # .....................
    @property
    def Editor(self) -> str:
        return self._Editor
    @Editor.setter
    def Editor(self, val: str) -> None:
        self._Editor=val

    # .....................
    @property
    def AlphabetizeIndividually(self) -> bool:
        return self._AlphabetizeIndividually
    @AlphabetizeIndividually.setter
    def AlphabetizeIndividually(self, val: bool) -> None:
        if val is None:
            val=[]
        self._AlphabetizeIndividually=val

    # .....................
    @property
    def Keywords(self) -> ParmDict:
        return self._Keywords
    # There is no setter
    def SetKeyword(self, kwd: str, val: str=""):
        self._Keywords[kwd]=val # If no value is supplied, we use ""


#

#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

class FanzineSerial:

    def __init__(self, Vol: None|int|str=None, Num: None|int|str|float=None, NumSuffix: str|None="", Whole:None|int|str|float=None, WSuffix: str|None="") -> None:
        self._Vol=None
        self._Num=None
        self._Whole=None
        self._WSuffix=""
        self._NumSuffix=""

        self.Vol=Vol
        self.Num=Num
        self.NumSuffix=NumSuffix  # For things like issue '17a'
        self.Whole=Whole
        self.WSuffix=WSuffix
        pass

    # List class properties: [p for p in dir(FanzineSerial) if isinstance(getattr(FanzineSerial, p), property)]

    # import inspect
    # All functions: [name for (name, value) in inspect.getmembers(FanzineSerial)]
    # All functions and instance variables: [(name, value) for (name, value) in inspect.getmembers(self)]
    # Just properties [(name, value) for (name, value) in inspect.getmembers(self, lambda o: isinstance(o, property))]
    # source code: inspect.getsource(FanzineIssueSpecList.List.fget)
    # inspect.getsource(FanzineSerial.Whole.fget)

    # -----------------------------
    # Are the Num fields equal?
    # Both could be None; otherwise both must be equal
    def __NumEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self._Num == other._Num and CaseInsensitiveCompare(self._NumSuffix, other._NumSuffix)

    # -----------------------------
    def __VolEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self._Vol == other._Vol

    # -----------------------------
    def __WEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self._Whole == other._Whole and CaseInsensitiveCompare(self._WSuffix, other._WSuffix)

    # -----------------------------
    def __VNEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self.__VolEq__(other) and self.__NumEq__(other)

    # -----------------------------
    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)
    def __eq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        # if the Whole numbers match, the two are the same. (Even if the Vol/Num differ.)
        if self._Whole is not None and self.__WEq__(other):
            return True
        # If the wholes match and the Vol/Num match, the two are the same
        if self.__WEq__(other) and self.__VNEq__(other):
            return True
        # if at least one of the Wholes is None and the Vol/Num match, the two are the same
        if (self._Whole is None or other._Whole is None) and self.__VNEq__(other):
            return True
        return False

    # -----------------------------
    def __ne__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return not self.__eq__(other)

    # -----------------------------
    # Define < operator for sorting
    # Is self less than other?
    def __lt__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        if other is None:
            return False
        # If both have Wholes, use Whole for the comparison
        if self._Whole is not None and other._Whole is not None:
            if self._Whole < other._Whole:
                return True
            if self._Whole > other._Whole:
                return False

            # Can the suffixes provide a tie breaker?
            if self._WSuffix is not None or other._WSuffix is not None:
                # OK, the Wholes are equal.  Can the suffixs (e.g., #133 and #133A) be used to distinguish?  Suffixed Wholes are always larger.
                if other._WSuffix is None:
                    return False            # If other is None it can't be less that self, even if self, also, is None
                if self._WSuffix is None:
                    return True             # Other has a suffix and self doesn't, so self is less than other
                # Both have suffixes
                return self._WSuffix < other._WSuffix

        # Wholes were no help
        if self._Vol is not None and other._Vol is not None:
            if self._Vol < other._Vol:
                return True
            if self._Vol > other._Vol:
                return False
            # The Vols are equal; Check the numbers within the volume
            if self._Num is None and other._Num is None:
                return False
            if self._Num is None and other._Num is not None:
                return True
            if self._Num is not None and other._Num is None:
                return False

        # Who knows?
        return False

    # -----------------------------
    def Copy(self, other: FanzineSerial) -> None:             # FanzineSerial
        self._Vol=other._Vol
        self._Num=other._Num
        self._NumSuffix=other._NumSuffix
        self._Whole=other._Whole
        self._WSuffix=other._WSuffix


    # -----------------------------
    def SetIntProperty(self, val: None|int|str) -> int|None:
        if val is None:
            return None
        elif isinstance(val, str):
            return ToNumeric(val)
        return val

    # .....................
    @property
    def Vol(self) -> int|None:          
        return self._Vol

    @Vol.setter
    def Vol(self, val: None|int|str) -> None:             # FanzineSerial
        self._Vol=self.SetIntProperty(val)

    # .....................
    @property
    def Num(self) -> int|None:         
        return self._Num

    @Num.setter
    def Num(self, val: None|int|str) -> None:             # FanzineSerial
        self._Num=self.SetIntProperty(val)

    # .....................
    @property
    def NumSuffix(self) -> str|None:        
        return self._NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val: str|None) -> None:        
        if val is None:
            val=""
        self._NumSuffix=val

    # .....................
    @property
    def Whole(self) -> int|None:            
        return self._Whole

    @Whole.setter
    def Whole(self, val: None|int|str) -> None:             # FanzineSerial
        self._Whole=self.SetIntProperty(val)

    # .....................
    @property
    def WSuffix(self) -> str|None:
        return self._WSuffix
    @WSuffix.setter
    def WSuffix(self, val: str|None) -> None:          
        if val is None:
            val=""
        self._WSuffix=val

    # .....................
    # Does this instance have anything defined for the serial number?
    def IsEmpty(self) -> bool:             # FanzineSerial
        if self._NumSuffix is not None and len(self._NumSuffix) > 0:
            return False
        if self._Num is not None:
            return False
        if self._Whole is not None:
            return False
        if self._Vol is not None:
            return False
        if self._WSuffix is not None and len(self._WSuffix) > 0:
            return False
        return True

    # .......................
    # Convert the FanzineIssueSpec into a debugging form
    def __repr__(self) -> str:             # FanzineSerial

        v="-"
        if self.Vol is not None:
            v=str(self.Vol)
        n="-"
        if self.Num is not None:
            n=str(self.Num)
            if self.NumSuffix is not None:
                n+=str(self.NumSuffix)
        w="-"
        if self.Whole is not None:
            w=str(self.Whole)
            if self.WSuffix is not None:
                w+=str(self.WSuffix)

        s="V"+v+", N"+n+", W"+w
        return s

    # .......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self) -> str:             # FanzineSerial
        tg=""

        if self.Vol is not None and self.Num is not None and self.Whole is not None:
            s="V"+str(self.Vol)+"#"+str(self.Num)
            if self.NumSuffix is not None:
                s+=str(self.NumSuffix)
            s+=" (#"+str(self.Whole)
            if self.WSuffix is not None:
                s+=str(self.WSuffix)
            s+=")"
            tg=(s+tg).strip()

        elif self.Vol is not None and self.Num is not None:
            s="V"+str(self.Vol)+"#"+str(self.Num)
            if self.NumSuffix is not None:
                s+=str(self.NumSuffix)
            tg=(s+tg).strip()

        elif self.Whole is not None:
            s="#"+str(self.Whole)
            if self.WSuffix is not None:
                s+=str(self.WSuffix)
            tg=(s+tg).strip()

        return tg.strip()

     # =====================================================================================
        # Function to attempt to decode an issue designation into a volume and number
        # Return a tuple of Volume and Number
        # If there's no volume specified, Volume is None and Number is the whole number
        # If we can't make sense of it, return (None, None), so if the 2nd member of the tuple is None, conversion failed.
    def DecodeIssueDesignation(self, s: str) -> tuple[ int|None, int|None ]:            
        with suppress(Exception):
            return None, int(s)

        # Ok, it's not a simple number.  Drop leading and trailing spaces and see if it of the form #nn
        s=s.strip().lower()
        if len(s) == 0:
            return None, None
        if s[0] == "#":
            s=s[1:]
            if len(s) == 0:
                return None, None
            with suppress(Exception):
                return None, int(s)

        # This exhausts the single number possibilities
        # Maybe it's of the form Vnn, #nn (or Vnn.nn or Vnn,#nn)

        # Strip any leading 'v'
        if len(s) == 0:
            return None, None
        if s[0] == "v":
            s=s[1:]
            if len(s) == 0:
                return None, None

        # The first step is to see if there's at least one of the characters ' ', '.', and '#' in the middle
        # We split the string in two by a span of " .#"
        # Walk through the string until we;ve passed the first span of digits.  Then look for a span of " .#". The look for at least one more digit.
        # Since we've dropped any leading 'v', we kno we must be of the form nn< .#>nnn
        # So if the first character is not a digit, we give up.
        if not s[0].isdigit():
            return None, None

        # Now, the only legitimate character other than digits are the three delimiters, so translate them all to blanks and then split into the two digit strings
        spl=s.replace(".", " ").replace("#", " ").split()
        if len(spl) != 2:
            return None, None
        with suppress(Exception):
            return int(spl[0]), int(spl[1])

        return None, None


    # =============================================================================
    # Format the Vol/Num/Whole information
    def FormatSerialForSorting(self) -> str:             # FanzineSerial
        if self.Whole is not None and self.Vol is not None and self.Num is not None:
            return "#"+"{0:7.2f}".format(self.Whole)+"  (V"+"{0:7.2f}".format(self.Vol)+"#"+"{0:7.2f}".format(self.Num)+")"+self.NumSuffix

        if self.Whole is not None:
            return "#"+"{0:7.2f}".format(self.Whole)+self._WSuffix

        if self.Vol is None and self.Num is None:
            return "0000.00"

        v="0000.00"
        n="0000.00"
        if self.Vol is not None:
            v="{0:7.2f}".format(self.Vol)
        if self.Num is not None:
            n="{0:7.2f}".format(self.Num)

        return "V"+v+"#"+n+self.NumSuffix

    # =============================================================================================
    # Try to interpret a complex string as serial information
    # If there's a trailing Vol+Num designation at the end of a string, interpret it.
    #  leading=True means that we don't try to match the entire input, but just a greedy chunk at the beginning.
    #  strict=True means that we will not match potentially ambiguous or ill-formed strings
    # complete=True means that we will only match the *complete* input (other than leading and trailing whitespace).

    # We accept:
    #       ...Vnn[,][ ]#nnn[ ]
    #       ...nnn nnn/nnn      a number followed by a fraction
    #       ...nnn/nnn[  ]      vol/num
    #       ...rrr/nnn          vol (in Roman numerals)/num
    #       ...nn.mm
    #       ...nn[ ]
    @classmethod
    def Match(cls, s: str, scan: bool=False, strict: bool=False, complete: bool=False):             # FanzineSerial
        s=s.strip()     # Remove leading and trailing whitespace

        # First look for a Vol+Num designation: Vnnn #mmm
        pat=r"^V(\d+)\s*#(\d+)(\w?)"
        # # Leading junk
        # Vnnn + optional whitespace
        # #nnn + optional single alphabetic character suffix
        m=re.match(pat, s)
        if m is not None and len(m.groups()) in [2, 3]:
            ns=None
            if len(m.groups()) == 3:
                ns=m.groups()[2]
            return cls(Vol=int(m.groups()[0]), Num=int(m.groups()[1]), NumSuffix=ns)

        #
        #  Vol (or VOL) + optional space + nnn + optional comma + optional space
        # + #nnn + optional single alphabetic character suffix
        m=re.match(r"V[oO][lL]\s*(\d+)\s*#(\d+)(\w?)$", s)
        if m is not None and len(m.groups()) in [2, 3]:
            ns=None
            if len(m.groups()) == 3:
                ns=m.groups()[2]
            return cls(Vol=int(m.groups()[0]), Num=int(m.groups()[1]), NumSuffix=ns)

        # Now look for nnn nnn/nnn (fractions!)
        # nnn + mandatory whitespace + nnn + slash + nnn * optional whitespace
        m=re.match(r"^(\d+)\s+(\d+)/(\d+)$", s)
        if m is not None and len(m.groups()) == 3:
            return cls(Whole=int(m.groups()[0])+int(m.groups()[1])/int(m.groups()[2]))

        # Now look for nnn/nnn (which is understood as vol/num
        # Leading stuff + nnn + slash + nnn * optional whitespace
        m=re.match(r"^(\d+)/(\d+)$", s)
        if m is not None and len(m.groups()) == 2:
            return cls(Vol=int(m.groups()[0]), Num=int(m.groups()[1]))

        # Now look for xxx/nnn, where xxx is in Roman numerals
        # Leading whitespace + roman numeral characters + slash + nnn + whitespace
        m=re.match(r"^([IVXLC]+)/(\d+)$", s)
        if m is not None and len(m.groups()) == 2:
            #TODO: the regex detects more than just Roman numerals.  We need to bail out of this branch if that happens and not return
            return cls(Vol=InterpretRoman(m.groups()[0]), Num=int(m.groups()[1]))

        # Next look for nnn-nnn (which is a range of issue numbers; only the start is returned)
        # Leading stuff + nnn + dash + nnn
        m=re.match(r"^(\d+)-(\d+)$", s)
        if m is not None and len(m.groups()) == 2:
            return cls(Whole=int(m.groups()[0]))

        # Next look for #nnn
        # Leading stuff + nnn
        m=re.match(r"^#(\d+)$", s)
        if m is not None and len(m.groups()) == 1:
            return cls(Whole=int(m.groups()[0]))

        # Now look for a trailing decimal number
        # Leading characters + single non-digit + nnn + dot + nnn + whitespace
        # the ? makes * a non-greedy quantifier
        m=re.match(r"^.*?(\d+\.\d+)$", s)
        if m is not None and len(m.groups()) == 1:
            return cls(Num=float(m.groups()[0]))

        if not strict and not complete:
            # Now look for a single trailing number
            # Leading stuff + nnn + optional single alphabetic character suffix + whitespace
            m=re.match(r"^.*?([0-9]+)([a-zA-Z]?)\s*$", s)
            if m is not None and len(m.groups()) in [1, 2]:
                ws=None
                if len(m.groups()) == 2:
                    ws=m.groups()[1].strip()
                return cls(Whole=int(m.groups()[0]), WSuffix=ws)

            # Now look for trailing Roman numerals
            # Leading stuff + mandatory whitespace + roman numeral characters + optional trailing whitespace
            m=re.match(r"^.*?\s+([IVXLC]+)\s*$", s)
            if m is not None and len(m.groups()) == 1:
                return cls(Num=InterpretRoman(m.groups()[0]))

        # No good, return failure
        return cls()


#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
class FanzineIssueSpec:

    def __init__(self, Vol: None|int|str=None,
                 Num: None|int|str=None,
                 NumSuffix: str|None=None,
                 Whole: None|int|str=None,
                 WSuffix: str|None=None,
                 Year: int|None=None,
                 Month: int|None=None,
                 MonthText: str|None=None,
                 Day: int|None=None,
                 DayText: str|None=None,
                 FS: FanzineSerial|None=None,
                 FD: FanzineDate|None=None)\
            -> None:

        if FS is not None:
            self._FS=FS
        else:
            self._FS=FanzineSerial(Vol=Vol, Num=Num, NumSuffix=NumSuffix, Whole=Whole, WSuffix=WSuffix)

        if FD is not None:
            self._FD=FD
        else:
            self._FD=FanzineDate(Year=Year, Month=Month, MonthText=MonthText, Day=Day, DayText=DayText)

    # .......................
    # Convert the FanzineIssueSpec into a debugging form
    def __repr__(self) -> str:  # FanzineIssueSpec
        s="IS("+repr(self._FS)+" "+repr(self._FD)
        s=s+")"

        return s

    # .......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self) -> str:  # FanzineIssueSpec
        tg=""
        if not self._FD.IsEmpty():
            tg+=" "+str(self._FD)

        if not self._FS.IsEmpty():
            tg+="  "+str(self._FS)

        return tg.strip()


    # .......................
    # Convert the FanzineIssueSpec into the shortest pretty string that identifies the issue
    def IssueDesignation(self) -> str:
        if not self._FS.IsEmpty():
            return str(self._FS)
        if not self._FD.IsEmpty():
            return str(self._FD)
        return ""


    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)

    # Class equality check.
    def __eq__(self, other: FanzineIssueSpec) -> bool:         
        return self._FS == other._FS and self._FD == other._FD

    def __ne__(self, other: FanzineIssueSpec):         
        return not self.__eq__(other)

    #-----------------------------
    # Define < operator for sorting
    def __lt__(self, other: FanzineIssueSpec) -> bool:         
        if other is None:
            return False
        if self._FD is not None and other._FD is not None:
            return self._FD < other._FD
        if self._FS is not None and other._FS is not None:
            return self._FS < other._FS
        return False

    def Copy(self, other: FanzineIssueSpec) -> None:        
        self._FD=other._FD
        self._FS=other._FS

    def DeepCopy(self, other: FanzineIssueSpec) -> None:
        self.Vol=other.Vol
        self.Num=other.Num
        self.NumSuffix=other.NumSuffix
        self.Whole=other.Whole
        self.WSuffix=other.WSuffix
        self.Year=other.Year
        self.Month=other.Month
        self.Day=other.Day
        self.FS.Copy(other.FS)
        self.FD.Copy(other.FD)


    # .....................
    @property
    def FD(self) -> FanzineDate|None:       
        return self._FD

    @FD.setter
    def FD(self, val: FanzineDate) -> None:         
        self._FD=val

    # .....................
    @property
    def FS(self) ->FanzineSerial|None:        
        return self._FS

    @FS.setter
    def FS(self, val: FanzineSerial) -> None:
        self._FS=val

    # .....................
    @property
    def Vol(self) -> int|None:       
        return self._FS.Vol

    @Vol.setter
    def Vol(self, val: int|str|None) -> None:        
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.Vol=None
        else:
            self._FS.Vol=ToNumeric(val)

    # .....................
    @property
    def Num(self) -> int|None:        
        return self._FS.Num

    @Num.setter
    def Num(self, val: int|str|None) -> None:        
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.Num=None
        else:
            self._FS.Num=ToNumeric(val)

    # .....................
    @property
    def NumSuffix(self) -> str|None:       
        return self._FS.NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val: str|None) -> None:        
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.NumSuffix=None
        else:
            self._FS.NumSuffix=val

    #.....................
    @property
    def Whole(self) -> int|None:     
        return self._FS.Whole

    @Whole.setter
    def Whole(self, val: int|str|None)-> None:      
        print("Setting _FS.Whole to "+str(val))
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.Whole=None
        else:
            self._FS.Whole=ToNumeric(val)


    # .....................
    @property
    def WSuffix(self) -> str|None:        
        return self._FS.WSuffix

    @WSuffix.setter
    def WSuffix(self, val: str|None) -> None:        
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.WSuffix=None
        else:
            self._FS.WSuffix=val

    #.....................
    @property
    def Year(self) -> int|None:         
        return self._FD.Year

    @Year.setter
    def Year(self, val: int|str|None)-> None:   
        self._FS.Year=val

    #.....................
    # This is a non-settable property -- it is always derived from the numeric Year
    @property
    def YearText(self) -> str|None:     
        return self._FD.YearText

    #.....................
    @property
    def MonthNum(self) ->int|None:
        return self._FD.MonthNum

    @property
    def Month(self) -> int|None:
        assert False
    @Month.setter
    def Month(self, val: int|str|None)-> None:      
        self._FD.Month=val

    #.....................
    @property
    def MonthText(self) -> str|None:      
        return self._FD.MonthName


    #.....................
    @property
    def Day(self) -> int|None:           
        return self._FD.Day

    @Day.setter
    def Day(self, val: int|None) -> None:      
        self._FD.Day=val

    # .....................
    @property
    def DayText(self) -> str|None:      
        return self._FD.DayText
    # There is no setter; Setting should be done when creating the instance or through the Day setter

    #.....................
    @property
    def DateStr(self) -> str:                
        return str(self._FD)

    @property
    def MonthYear(self) -> str:
        s=self.MonthText+" "+self.YearText
        return s.strip()

    @property
    def SerialStr(self) -> str:                 
        return str(self._FS)

    # .....................
    # Return a datetime.date object
    def Date(self) -> datetime.date:                    
        return self._FD.Date

    #.......................
    def IsEmpty(self) -> bool:                          
        return self._FD.IsEmpty() and self._FS.IsEmpty()


    # =====================================================================================
#    def DecodeIssueDesignation(self, s: str) -> None:       
#        self._FS.DecodeIssueDesignation(s)


    # =====================================================================================
    # Take the input string and turn it into a FIS
    # The input could be a single date or it could be a single serial ID or it could be a range (e.g., 12-17)
    @classmethod
    def Match(cls, s: str, strict: bool = False, complete: bool=False):                  

        # A number standing by itself is messy, since it's easy to confuse with a date
        # In the FanzineIssueSpec world, we will always treat it as a Serial, so look for that first
        m=re.match(r"^(\d+)$", s)
        if m is not None and len(m.groups()) == 1:
            w=m.groups()[0]
            fs=FanzineSerial(Whole=w)
            return cls(FS=fs)

        # First try a date, and interpret it strictly no matter what the parameter says -- we can try non-strict later
        fd=FanzineDate().Match(s, strict=True, complete=True)
        if not fd.IsEmpty():
            return cls(FD=fd)

        # OK, it's probably not a date.  So try it as a serial ID
        fs=FanzineSerial().Match(s, strict=strict, complete=True)
        if not fs.IsEmpty():
            return cls(FS=fs)

        # That didn't work, either.  Try a non-strict date followed by a non-strict serial
        # OK, it's probably not a date.  So try it as a serial ID
        fs=FanzineSerial().Match(s, complete=complete)
        if not fs.IsEmpty():
            return cls(FS=fs)

        # No good.  Failed.
        return cls()


    # =====================================================================================
    # Look for a FIS in the input string.  Return a tuple of (success, <unmatched text>)
    def Scan(self, s: str, strict: bool=False) -> tuple[bool, str]:        
        raise Exception


    #=============================================================================
    def FormatYearMonthForSorting(self) -> str:
        return self._FD.FormatYearMonthForSorting()

    def FormatYearMonthDayForSorting(self) -> str:
        return self._FD.FormatYearMonthDayForSorting()

    #=============================================================================
    # Format the Vol/Num/Whole information
    def FormatSerialForSorting(self) -> str:         
        return self._FS.FormatSerialForSorting()

######################################################################################################################
######################################################################################################################
# Now define class FanzineIssueSpecList
######################################################################################################################
######################################################################################################################
# A Fanzine issue spec list contains the information to handle a list of issues of a single fanzine.
# It includes the series name, editors(s), and a list of Fanzine IssueName specs.
#TODO: This can be profitably extended by changing the FISL class to include specific names and editors for each issue, since sometimes
#TODO: a series does not have a consistent set throughout.

class FanzineIssueSpecList:
    def __init__(self, List: list[FanzineIssueSpec]|None=None) -> None:
        self._List=None
        self.List=List  # Use setter
        pass

    # ...............................
    def AppendIS(self, fanzineIssueSpec: None|FanzineIssueSpec|FanzineIssueSpecList) -> None:      
        if fanzineIssueSpec is None:
            return
        self.Extend(fanzineIssueSpec)
        return

    # ...............................
    # Basically, this is just a synonym for Extend
    def Append(self, lst: FanzineIssueSpecList|list[FanzineIssueSpec]|FanzineIssueSpec|None) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        return self.Extend(lst)

    # ...............................
    def Extend(self, val: FanzineIssueSpecList|list[FanzineIssueSpec, FanzineIssueSpec, None]) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        if self._List is None:
            self._List=[]

        if isinstance(val, FanzineIssueSpecList):
            lst=val.List
            if lst is None or len(lst) == 0:
                pass      # Nothing to do
            else:
                self._List.extend(lst)
        elif isinstance(val, list):
            if len(val) == 0:
                pass        # Nothing to do
            else:
                self._List.extend(val)
        elif isinstance(val, FanzineIssueSpec):
            self._List.append(val)
        else:
            Exception("FanzineIssueSpecList.Extend: Uninterpretable val type")
        return self

    # ...............................
    def IsEmpty(self) -> bool:      
        if self._List is None or len(self._List) == 0:
            return True
        # Next we go through the elements of the list. If *any* element is non-empty, then the whole FISL is non-empty
        for fis in self._List:
            if not fis.IsEmpty():
                return False
        return True

    # ...............................
    def __repr__(self) -> str:      
        s=""
        if self._List is not None:
            for i in self:
                if len(s) > 0:
                    s=s+",  "
                if i is not None:
                    s=s+repr(i)
                else:
                    s=s+"Missing ISList"
        if len(s) == 0:
            s="Empty ISlist"
        return s


    #...............................
    def __str__(self) -> str:   # Format the ISL for pretty      
        s=""
        for i in self:
            if i is not None:
                if len(s) > 0:
                    s=s+", "
                s=s+str(i)
        return "FISL("+str(len(self._List))+"): "+s

    # ...............................
    def __len__(self) -> int:
        if self._List is None:
            return 0
        return len(self._List)

    # ...............................
    @property
    def List(self) -> FanzineIssueSpecList:      
        return self._List

    @List.setter
    def List(self, val: FanzineIssueSpec|FanzineIssueSpecList|None) -> None:
        if val is None:
            self._List=[]
            return
        if isinstance(val, FanzineIssueSpec):
            self._List=[val]
            return
        if isinstance(val, FanzineIssueSpecList):
            self._List=val.List
            return
        if isinstance(val, list):
            if len(val) == 0:
                self._List=[]
                return
            if isinstance(val[0], FanzineIssueSpec):
                self._List=val
                return
        Log("****FanzineIssueSpecList.List setter() had strange input: "+str(val))

    #-----------------------------------
    # Iterators which allow a FanzineIssueSpecList to be iterated directly and not through _List
    def __getitem__(self, key: int) -> FanzineIssueSpec:      # FanzineIssueSpecList
        return self._List[key]

    def __setitem__(self, key: int, value: FanzineIssueSpec) -> FanzineIssueSpecList:      
        self.List[key]=value
        return self


    # =====================================================================================
    # Pull a Serial off of the end of a string, returning a FISL and the remainder of the string
    def GetTrailingSerial(self, s: str) -> tuple[FanzineIssueSpecList|None, str]:       
        # Try to greedily (reverse-greedily?) interpret the trailing text as a FanzineIssueSpec.
        # We do this by interpreting more and more tokens starting from the end until we have something that is no longer recognizable as a FanzineIssueSpec
        # The just-previous set of tokens constitutes the full IssueSpec, and the remaining leading tokens are the series name.
        tokens=s.split()  # Split into tokens on spaces
        if len(tokens) == 0:
            return None, s

        leadingText=" ".join(tokens)
        longestFISL=None
        for index in range(len(tokens)-1, -1, -1):  # Ugly, but I need index to be the indexes of the tokens
            trailingText=" ".join(tokens[index:])
            leadingText=" ".join(tokens[:index])
            print("     index="+str(index)+"   leading='"+leadingText+"'    trailing='"+trailingText+"'")
            trialFISL=FanzineIssueSpecList().Match(trailingText, strict=True, complete=True)  # Failed.  We've gone one too far. Quit trying and use what we found on the previous iteration
            if trialFISL.IsEmpty():
                print("     ...backtracking. Found FISL="+repr(trialFISL))
                leadingText=" ".join(tokens[0:index+1])
                break
            longestFISL=trialFISL
        # At this point, leadingText is the fanzine's series name and longestFISL is a list of FanzineSerials found for it
        print("     Found: "+str(longestFISL))
        return longestFISL, leadingText

    #------------------------------------------------------------------------------------
    # Take the input string and turn it into a FISL
    # The input string is a comma-separated list of issue numbers and dates, including ranges:
    # 1, 2, 3, 7, 9-12, 14A, V7#40, VIII, IX, 99, Jan 1999, March 31, 2005, 2007
    # The one place we allow internal commas is in a date where the month/day can be separated from the year by a comma.
    @classmethod
    def Match(cls, s: str, strict: bool=False, complete: bool=False) -> FanzineIssueSpecList:      
        fislist: list[FanzineIssueSpec]=[]      # Accumulate the list of FISs here

        tokens=[t.strip() for t in s.split(",")]        # Split the input on commas

        # The strategy will be to worth through the list of issue information, taking one at a time.
        while len(tokens) > 0:
            # Because some legitimate FISs have an internal comma, they may have been split into two tokens, so we first joing the leading two tokens and see if they make sense
            # If there are at least two tokens left, re-join them and see if the result is an FIS of the form <Month> [day], yyyy
            # We can't allow 2-digit years here because they are indistinguishable from issue numbers.
            if len(tokens) > 1:
                #TODO: We are currently being very conservative in what we recognize here.  This might well be improved.
                # Token 0 must contain a month name as its first token and may not start with a digit
                if not tokens[0][0].isdigit() and MonthNameToInt(tokens[0].split()[0]) is not None:
                    # Token 1 must be a 4-digit year
                    if re.match(r"^\d{4}$", tokens[1]) is not None:
                        # The put them together and try to interpret as a date
                        trial=tokens[0]+", "+tokens[1]
                        fis=FanzineIssueSpec().Match(trial, strict=True, complete=True)    # This match must consume the entire input -- no partial matches
                        if not fis.IsEmpty():
                            fislist.append(fis)
                            del tokens[0:1]     # Delete both leading tokens.
                            continue

            # Interpreting the first two tokensas one  didn't work, so now try just the first token
            # The first thing to look for is a range denoting multiple issues.  This will necessarily contain a hyphen, which can only appear to denote a range
            # nnn-nnn
            #TODO: Consider also handling date ranges, e.g., Jan-Jun 2001
            if "-" in tokens[0]:
                subtokens=tokens[0].split("-")
                # For now, at least, we can only handle the case of two subtokens, both of which are integers with the first the smaller
                if len(subtokens) != 2:
                    Log("FanzineIssueSpecList:Match: More than one hyphen found in '"+s+"'")
                    return cls()
                if not IsInt(subtokens[0]) or not IsInt(subtokens[1]) or int(subtokens[0]) >= int(subtokens[1]):
                    Log("FanzineIssueSpecList:Match: bad range values in '"+s+"'")
                    return cls()
                for i in range(int(subtokens[0]), int(subtokens[1])+1):
                    fislist.append(FanzineIssueSpec(Whole=i))
                del tokens[0]
                continue

            # It's neither a group including a comma nor a range.  Try to interpret the token as a single FIS
            # Now just look for a single issue
            # nnn or Vnn #nn or variants or dates, etc.
            fis=FanzineIssueSpec().Match(tokens[0], strict=strict, complete=complete)
            if not fis.IsEmpty():
                fislist.append(fis)
                del tokens[0]
                continue

            # Nothing worked, so we won't have an FISL
            Log("FanzineIssueSpecList.Match can't interpret '"+str(tokens[0]+"' as an issue spec.  It is ignored."))
            del tokens[0]

        # We have consumed the whole input.  Return a FISL
        return cls(List=fislist)


    #------------------------------------------------------------------------------------
    # Look for a FISL in the input string.  Return a tuple of (success, <unmatched text>)
    def Scan(self, s: str, strict: bool=False) -> tuple[bool, str]:      
        raise Exception


######################################################################################################################
######################################################################################################################
# FanacIssueInfo
######################################################################################################################
#####################################################################################################################

class FanzineIssueInfo:

    def __init__(self, Series: FanzineSeriesInfo|None=None, IssueName: str="", DisplayName: str="",
                 DirURL: str="", PageFilename: str="", FIS: FanzineIssueSpec|None=None, Position: int=-1,
                 Pagecount: int|None=None, Editor: str="", Country: str="", Taglist: list[str]=None, Mailings: list[str]=None, Temp: any=None, AlphabetizeIndividually: bool=False,
                 FanzineType: str="") -> None:
        _Series: FanzineSeriesInfo|None=None
        _IssueName: str=""      # Name of this issue (does not include issue #/date info)
        _DisplayName: str=""    # Name to use for this issue. Includes issue serial and or date
        _DirURL: str=""  # URL of fanzine directory
        _PageFilename: str=""  # URL of specific issue in directory
        _FIS: FanzineIssueSpec|None=None  # FIS for this issue
        _Position: int=-1        # The index in the source fanzine index table
        _Pagecount: int=0  # Page count for this issue
        _Editor: str=""     # The editor for this issue.  If None, use the editor of the series
        _Locale: Locale
        _Taglist: list[str]|None=None  # A list of tags for this fanzine (e.g., "newszine")
        _Mailings: list[str]=[]  # A List of APA mailings this issue was a part of
        _Temp: any=None     # Used outside the class to hold random information
        _AlphabetizeIndividually: bool=False
        _FanzineType: str=""

        # Use the properties to set the values for all of the instance variables. We do this so that any special setter processing is done with the init values.
        self.Series=Series
        self.IssueName=IssueName
        self.DisplayName=DisplayName
        self.DirURL=DirURL
        self.PageFilename=PageFilename
        self.FIS=FIS
        self._Position=Position
        self.Pagecount=Pagecount
        self.Editor=Editor
        self._Locale=Locale(Country)
        self.Taglist=Taglist
        self.Mailings=Mailings
        self.AlphabetizeIndividually=AlphabetizeIndividually
        self.Temp=Temp
        self._FanzineType=FanzineType

    # .....................
    def __str__(self) -> str:                       
        out=""
        if self.DisplayName != "":
            return self.DisplayName

        if self.IssueName != "":
            out=self.IssueName
        elif self.SeriesName != "":
            out=self.SeriesName

        if self.FIS is not None and len(str(self.FIS)) > 0:
            out+=" "+str(self.FIS)

        return out.strip()

    # .....................
    def __repr__(self) -> str:                       
        out=""
        if self.DisplayName != "":
            out="'"+self.DisplayName+"'"
        elif self.IssueName != "":
            out=self.IssueName
        elif self.SeriesName != "":
            out=self.SeriesName

        if self.FIS is not None and len(str(self.FIS)) > 0:
            out+=" {"+str(self.FIS)+"}"

        if self.Editor != "":
            out+="  ed:"+self.Editor
        if self.Pagecount is not None:
            out+="  "+str(self.Pagecount)+"pp"

        return out.strip()

    # .....................
    def __eq__(self, other:FanzineIssueInfo) -> bool:                       
        if self.SeriesName != other.SeriesName:
            return False
        if self._Editor != other._Editor:
            return False
        if self._IssueName != other._IssueName:
            return False
        if self._DisplayName != other._DisplayName:
            return False
        if self._DirURL != other._DirURL:
            return False
        if self._PageFilename != other._PageFilename:
            return False
        if self._Pagecount != other._Pagecount:
            return False
        if self._FanzineType != other._FanzineType:
            return False
        if self._FIS is not None and not self._FIS.IsEmpty():
            if other._FIS is None or other._FIS.IsEmpty():
                return False
            if self._FIS != other._FIS:
                return False
        return True


    def DeepCopy(self) -> FanzineIssueInfo:
        fz=FanzineIssueInfo(Series=self.Series, IssueName=self.IssueName, DisplayName=self.DisplayName, DirURL=self.DirURL,
                            PageFilename=self.PageFilename, FIS=self.FIS, Pagecount=self.Pagecount, Editor=self.Editor, Country="",
                            Taglist=None, Mailings=self.Mailings, Temp=self.Temp, FanzineType=self.FanzineType)
        # Do some touch-ups
        fz._Locale=self.Locale
        fz.Taglist=[x for x in self.Taglist]
        return fz

    # .....................
    def IsEmpty(self) -> bool:                       
        if self.SeriesName != "" or self.IssueName != "" or self._DisplayName != "" or self.DirURL != "" or self.PageFilename != "" or self.Pagecount > 0 or self.Editor != "" or self.Taglist or self.Mailings:
            return False
        return self.FIS.IsEmpty()

    # .....................
    @property
    def SeriesName(self) -> str:    
        if self._Series is None:
            return ""
        return self._Series.SeriesName
    @SeriesName.setter
    def SeriesName(self, val: str) -> None:                       
        assert False

    # .....................
    @property
    def Series(self) -> FanzineSeriesInfo:                       
        if self._Series is None:
            self._Series=FanzineSeriesInfo()
        return self._Series
    @Series.setter
    def Series(self, val: FanzineSeriesInfo|None) -> None:                       
        self._Series=val

    # .....................
    @property
    def IssueName(self) -> str:                       
        return self._IssueName
    @IssueName.setter
    def IssueName(self, val: str) -> None:                       
        self._IssueName=val.strip()

    # .....................
    @property
    def DisplayName(self) -> str:                       
        if self._DisplayName != "":
            return self._DisplayName
        if self.FIS is not None and self.SeriesName != "":
            return self.SeriesName+" "+str(self.FIS)
        return self.SeriesName
    @DisplayName.setter
    def DisplayName(self, val: str) -> None:                       
        self._DisplayName=val.strip()

    # .....................
    @property
    def DirURL(self) -> str:                       
        return self._DirURL
    @DirURL.setter
    def DirURL(self, val: str) -> None:                       
        self._DirURL=val

    # .....................
    @property
    def PageFilename(self) -> str:                       
        return self._PageFilename
    @PageFilename.setter
    def PageFilename(self, val: str) -> None:                       
        self._PageFilename=val.strip()

    # .....................
    # Generate a proper URL for the item
    @property
    def URL(self) -> str:

        if self is None or self.PageFilename == "":
            return "<no url>"

        return MergeURLs(self.DirURL, self.PageFilename)


    # .....................
    @property
    def Temp(self) -> any:                       
        return self._Temp
    @Temp.setter
    def Temp(self, val: any) -> None:                       
        self._Temp=val

    # .....................
    @property
    def FIS(self) -> FanzineIssueSpec|None:                       
        return self._FIS
    @FIS.setter
    def FIS(self, val: FanzineIssueSpec) -> None:                       
        self._FIS=val

    # .....................
    @property
    def Position(self) -> int|None:                       
        return self._Position
    @Position.setter
    def Position(self, val: int) -> None:                       
        self._Position=val

    # .....................
    @property
    def Locale(self) -> Locale:                       
        return self._Locale
    # @Locale.setter
    # def Locale(self, val: FanzineIssueSpec) -> None:                       
    #     self._Locale=val

    # .....................
    @property
    def Pagecount(self) -> int:                       
        return self._Pagecount if self._Pagecount > 0 else 1
    @Pagecount.setter
    def Pagecount(self, val: int) -> None:                      
        self._Pagecount=val

    # .....................
    @property
    def Editor(self) -> str:                       
        return self._Editor
    @Editor.setter
    def Editor(self, val: str) -> None:                       
        self._Editor=val

    # .....................
    @property
    def FanzineType(self) -> str:
        return self._FanzineType
    @FanzineType.setter
    def FanzineType(self, val: str) -> None:
        self._FanzineType=val

    # .....................
    @property
    def SeriesEditor(self) -> str:
        if self._Series.Editor is not None:
            return self._Series.Editor
        return self.Editor

    # .....................
    @property
    def Taglist(self) -> list[str]:  # FanzineIssueInfo
        return self._Taglist
    @Taglist.setter
    def Taglist(self, val: list[str]) -> None:  # FanzineIssueInfo
        if val is None:
            val=[]
        self._Taglist=val

    # .....................
    @property
    def Mailings(self) -> list[str]:  # FanzineIssueInfo
        return self._Mailings
    @Mailings.setter
    def Mailings(self, val: list[str]) -> None:  # FanzineIssueInfo
        if val is None:
            val=[]
        self._Mailings=val

    # .....................
    @property
    def AlphabetizeIndividually(self) -> bool:  # FanzineIssueInfo
        return self._AlphabetizeIndividually
    @AlphabetizeIndividually.setter
    def AlphabetizeIndividually(self, val: bool) -> None:  # FanzineIssueInfo
        if val is None:
            val=[]
        self._AlphabetizeIndividually=val


######################################################################################################################
######################################################################################################################
# FanzineSeriesList
######################################################################################################################
#####################################################################################################################

# This is a class used to hold a list of many issues of a single fanzine.
class FanzineSeriesList:

    def __init__(self)  -> None:
        self._FIIL: list[FanzineIssueInfo]|None=[]
        self._SeriesName: str=""
        self._Editor: str=""
        self._Eligible: bool|None=None     # Is this eligible for the Hugos in a year in question?
        self._Notes: str=""
        self._SeriesURL: str=""

    # .....................
    @property
    def SeriesName(self) -> str:            
        return self._SeriesName
    @SeriesName.setter
    def SeriesName(self, val: str) -> None:            
        self._SeriesName=val.strip()

    # .....................
    @property
    def Editor(self) -> str:            
        return self._Editor
    @Editor.setter
    def Editor(self, val: str) -> None:            
        self._Editor=val

    # .....................
    @property
    def Eligible(self) -> bool:            
        if self._Eligible is None:
            return False
        return self._Eligible
    @Eligible.setter
    def Eligible(self, val: bool) -> None:
        self._Eligible=val

    # .....................
    @property
    def FIIL(self) -> list[FanzineIssueInfo]|None:
        #TODO: If we're returning an FIIL independent of the FSL, shouldn't we fill in the values which would be gotten by reference to the FSL?
        return self._FIIL
    @FIIL.setter
    def FIIL(self, val: FanzineIssueSpecList|None) -> None:
        # If there is no existing list of FIIs, we create one from the FISL
        if self._FIIL is not None and len(self._FIIL) > 0:
            raise(Exception("FIIL setter: FIIL is non-empty"))
        self._FIIL=[]
        for el in val:
            self._FIIL.append(FanzineIssueInfo(FIS=el, Editor=self.Editor, DirURL=self.SeriesURL))

    # .....................
    @property
    def Notes(self) -> str:            
        return self._Notes
    @Notes.setter
    def Notes(self, val: str) -> None:            
        self._Notes=val.strip()

    # .....................
    @property
    def SeriesURL(self) -> str:            
        return self._SeriesURL
    @SeriesURL.setter
    def SeriesURL(self, val: str) -> None:            
        self._SeriesURL=val.strip()

    # .....................
    def __repr__(self) -> str:  # Convert the FSS into a debugging form            
        iil="-"
        if len(self._FIIL) > 0:
            iil=repr(self._FIIL)

        sn="-"
        if self._SeriesName != "":
            sn=self._SeriesName+" "

        ed="-"
        if self._Editor != "":
            ed=self._Editor+" "

        nt=""
        if self._Notes != "":
            nt+=self._Notes+" "

        el="-"
        if self._Eligible is not None:
            el="T" if self._Eligible else "F"+" "

        u="-"
        if self._SeriesURL != "":
            u=self._SeriesURL

        return "FSS(SN:"+sn+", IIL:"+iil+", Ed:"+ed+", NT:"+nt+", El:"+el+" URL="+u+")"

    # .....................
    def __str__(self) -> str:  # Pretty print the FSS            
        out=""
        if self.SeriesName != "":
            out=self.SeriesName

        if self._Editor != "":
            out+=f"   ({self._Editor})"

        if self._Notes != "":
            out+=f"   ({self._Notes}) "

        if self._FIIL is not None and len(self._FIIL) > 0:
            out+="  FIIL: "
            for i in self._FIIL:
                if not i.IsEmpty():
                    out+=str(i)+", "
        return out



