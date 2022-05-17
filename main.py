import os
import re, datetime
from datetime import timedelta
import fnmatch
import sys
import dateparser
import inspect
from dateutil import tz

fail_date = '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' #ex: 2018-08-29 22:12:56

#for searching in AMPM logs
AMPM_logging = '\d{1,2}:\d{2}:\d{2} [A-Z]{2} \d{1,2}[/]\d{2}[/]\d{4}' #ex: 7:05:12 PM 8/29/2018

#for searching verbose logs
#textual patterns:
verbose_logging_first_line_pattern = "Verbose logging started"
verbose_logging_last_line_pattern = "Verbose logging stopped:"
#date patterns:
verbose_logging_whole_date_first_line_pattern = '\d{2}[/]\d{2}[/]\d{4}  \d{2}:\d{2}:\d{2}' #ex: 08/29/2018  22:12:40
verbose_logging_hours_pattern = '\[\d{2}:\d{2}:\d{2}' #ex: 22:12:40

#for searching regular patterns
all_regular_patterns = '^\d{4}.|$\d{2}.|$\d{2}.{1,2}\d{2}:\d{2}:\d{2}'

#for searching dates that need to be parsed from strings with dateparser module
date_parser_pattern = '^\d{2}[/][A-Za-z]{3}[/]\d{4}:\d{2}:\d{2}:\d{2}' #ex: 31/Oct/2018:11:49:06
date_parser_pattern2_first_line_pattern = '[A-Za-z]{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
date_parser_pattern2_first_line_only_date = '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' #ex: 2018-08-29 22:12:40
date_parser_pattern2_other_lines_pattern = '^[A-Za-z]{3} \d{2} \d{2}:\d{2}:\d{2}' #ex: Aug 29 22:12:40

#date patterns for parsing to datetime object
date_pat1 = '%Y-%m-%d %H:%M:%S'
date_pat2 = '%m/%d/%Y  %H:%M:%S'
date_pat3 = '%H:%M:%S'
date_pat4 = '%Y-%m-%d.%H:%M:%S'
date_pat5 = '%Y/%m/%d %H:%M:%S'
date_pat6 = '%Y-%m-%d--%H:%M:%S'
date_pat7 = '%I:%M:%S %p %m/%d/%Y'
date_pat8 = '%Y%m%d %H:%M:%S'

def StackTraceCondition(line1): #todo: make all "prints" log
    name = inspect.stack()[3][3]
    if(name == "SearchInVerboseLogs" or name == "helperFunc"):
        if re.search(verbose_logging_hours_pattern, line1) is None:
            return True
    elif (name == "SearchWithDateParser"):
        if re.search(date_parser_pattern, line1) is None:
            return True
    name = inspect.stack()[2][3]
    if (name == "SearchWithDateParser2"):
        if re.search(date_parser_pattern2_other_lines_pattern, line1) is None:
            return True
    elif (name == "SearchWithRegularPatterns"):
        if re.search(all_regular_patterns, line1) is None:
            return True
    elif (name == "SearchWithAmpmPattern"):
        if re.search(AMPM_logging, line1) is None:
            return True
    else:
        return False

def WriteLogName(file_to_write_to, log_to_search_in):
    file_to_write_to.write("*******************************" + os.path.basename(
        log_to_search_in) + "*************************************" + "\n")

def ConvertDateFromUtc(dateToConvert):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    dateToConvert = dateToConvert.replace(tzinfo=from_zone).astimezone(to_zone)
    print(dateToConvert)
    return dateToConvert

def FindRegexInLineAndConvertToDate(line, regPatt, datePatt):
    dateCompared1 = re.search(regPatt, line)
    convertedDate = datetime.datetime.strptime(dateCompared1.group(), datePatt)
    return convertedDate

def FindTheFailDate(file_to_write_to, source):
    line_regex = re.compile(r".*Test finished.*$")
    try:
        with open(source) as f:
            for line in f:
                if line_regex.search(line):
                    match = re.search(fail_date, line)
                    date = datetime.datetime.strptime(match.group(), date_pat1)
                    file_to_write_to.write("The fail date is: " + str(date)+"\n")
                    return date
    except Exception as e:
        print ("error in finding the fail date" + str(e))

def CheckForStackTrace(source, line_to_check_stack_after, file_to_write_to):
    foundLine = False
    try:
        with open(source) as f:
            for line1 in f:
                if(foundLine == True):
                    if(line1 == ''):
                        file_to_write_to.write(""+"\n")
                    elif (StackTraceCondition(line1)):
                        file_to_write_to.write(line1+"\n")
                        print (line1 + "\n")
                    else:
                        return True
                if(foundLine == False and str(line1)!= str(line_to_check_stack_after)):
                    pass
                else:
                    foundLine = True
    except Exception as e:
        print ("couldn't extract stacktrace " + str(e)+"\n")
    return

def SpecialConversions(pattern, line, relevantDatePat, verboseDateOptional = None):
    if(pattern == verbose_logging_hours_pattern):
        pattern = pattern.replace('\\[', "", 1)
        dateCompared = FindRegexInLineAndConvertToDate(line, pattern, relevantDatePat).replace(year=verboseDateOptional.year, month=verboseDateOptional.month,
                                                                                               day=verboseDateOptional.day)
    else:
        dateCompared = re.search(date_parser_pattern, line).group().replace(':', " ", 1)
        dateCompared = dateparser.parse(dateCompared)

    return dateCompared

def TimeIsInRangeOfOneMinAway(dateCompared, date):
    return ((dateCompared) <= date + timedelta(minutes=1) and (dateCompared) >= date - timedelta(minutes=1))

def OpenFileAndCheckWherePatternExists(date, file_to_write_to, log_to_search_in, pattern, first_line_was_printed,
                                       relevantDatePat = None, verboseDateOptional=None):
    name = inspect.stack()[2][3]
    with open(log_to_search_in) as k:
        for line in k:
            if (re.search(re.compile(pattern), line) != None):
                if (name == "SearchInVerboseLogs"): #means we arent in first verbose line checking
                    dateCompared = SpecialConversions(pattern, line, relevantDatePat, verboseDateOptional)
                elif(name == "SearchTheDateInCurrentLog"): #means we are in dateparser
                    dateCompared = SpecialConversions(pattern, line, relevantDatePat)
                else:
                    dateCompared = FindRegexInLineAndConvertToDate(line, pattern, relevantDatePat)
                if (TimeIsInRangeOfOneMinAway(dateCompared, date)):
                    if (first_line_was_printed == 0):
                        WriteLogName(file_to_write_to, log_to_search_in)
                        first_line_was_printed = 1
                    file_to_write_to.write(line + "\n")
                    CheckForStackTrace(log_to_search_in, line, file_to_write_to)
    return dateCompared, first_line_was_printed

def SearchInVerboseLogs(log_to_search_in, file_to_write_to, date):
    first_line_was_printed = 0
    try:
        with open(log_to_search_in) as f:
            first_line = f.readline()
            verboseDate = FindRegexInLineAndConvertToDate(first_line, verbose_logging_whole_date_first_line_pattern, date_pat2)
            if (TimeIsInRangeOfOneMinAway(verboseDate, date)):
                if (first_line_was_printed == 0):
                    WriteLogName(file_to_write_to, log_to_search_in)
                    first_line_was_printed = 1
                file_to_write_to.write(first_line + "\n")
            first_line_was_printed =1
        def helperFunc():
            (OpenFileAndCheckWherePatternExists(date, file_to_write_to, log_to_search_in,
                                                verbose_logging_hours_pattern, first_line_was_printed, date_pat3,
                                                verboseDate))
        helperFunc()
    except Exception as e:
        print ("error in verbose logs" + str(e))

def SearchWithDateParser(log_to_search_in, file_to_write_to, date):
    first_line_was_printed = 0
    try:
        OpenFileAndCheckWherePatternExists(date, file_to_write_to, log_to_search_in, date_parser_pattern,
                                           first_line_was_printed)
    except Exception as e:
        print ("error in dateparser1 logs" + str(e))


def SearchWithDateParser2(log_to_search_in, file_to_write_to, date): #todo: deal with naive/not naive timezone comparison
    first_line_was_printed = 0
    try:
        with open(log_to_search_in) as k:
            for line in k:
                if (re.search(re.compile(date_parser_pattern2_first_line_pattern), line) != None):
                    dateCompared = FindRegexInLineAndConvertToDate(line, date_parser_pattern2_first_line_only_date, date_pat1)
                    dateCompared = ConvertDateFromUtc(dateCompared)
                    if ((dateCompared) <= date + timedelta(minutes=1) and (dateCompared) >= date - timedelta(minutes=1)):
                        if(first_line_was_printed == 0):
                            WriteLogName(file_to_write_to, log_to_search_in)
                            first_line_was_printed = 1
                        file_to_write_to.write(line+"\n")
                        break
            for line in k:
                if (re.search(re.compile(date_parser_pattern2_other_lines_pattern), line) != None):
                    date_to_parse = re.search(date_parser_pattern2_other_lines_pattern, line).group()
                    date_to_parse = str(dateCompared.year)+" "+date_to_parse
                    parsedDate = dateparser.parse(date_to_parse)
                    parsedDate = ConvertDateFromUtc(parsedDate)
                    if ((parsedDate) <= date + timedelta(minutes=1) and (parsedDate) >= date - timedelta(minutes=1)):
                        if (first_line_was_printed == 0):
                            WriteLogName(file_to_write_to, log_to_search_in)
                            first_line_was_printed = 1
                        file_to_write_to.write(line+"\n")
                        CheckForStackTrace(log_to_search_in, line, file_to_write_to)
    except Exception as e:
        print ("error in dateparser2 logs" + str(e))


def SearchExactRegularPattern(line):
    dateCompared1 = re.search(all_regular_patterns, line)
    try:
        date_to_compare = datetime.datetime.strptime(dateCompared1.group(), date_pat1)
        return date_to_compare
    except Exception as e:
        print ("error in regular patterns logs" + str(e))
        try:
            date_to_compare = datetime.datetime.strptime(dateCompared1.group(), date_pat4)
            return date_to_compare
        except Exception as e:
            print ("error in regular patterns logs" + str(e))
            try:
                date_to_compare = datetime.datetime.strptime(dateCompared1.group(), date_pat5)
                return date_to_compare
            except Exception as e:
                print("error in regular patterns logs" + str(e))
                try:
                    date_to_compare = datetime.datetime.strptime(dateCompared1.group(), date_pat6)
                    return date_to_compare
                except Exception as e:
                    print ("error in regular patterns logs" + str(e))
                    try:
                        date_to_compare = datetime.datetime.strptime(dateCompared1.group(), date_pat8)
                        return date_to_compare
                    except Exception as e:
                        print ("error in regular patterns logs" + str(e))
                        return None

    return None


def SearchWithRegularPatterns(log_to_search_in, file_to_write_to, date):
    first_line_was_printed = 0
    try:
        with open(log_to_search_in) as f:
            for line in f:
                date_to_compare = SearchExactRegularPattern(line)
                if(date_to_compare != None):
                    if (date_to_compare) <= date + timedelta(minutes=1) and (date_to_compare) >= date - timedelta(minutes=1):
                        if(first_line_was_printed == 0):
                            WriteLogName(file_to_write_to, log_to_search_in)
                            first_line_was_printed = 1
                        file_to_write_to.write(line+"\n")
                        CheckForStackTrace(log_to_search_in, line, file_to_write_to)
    except Exception as e:
        print ("error in regular patterns logs" + str(e))


def SearchWithAmpmPattern(log_to_search_in, file_to_write_to, date):
    first_line_was_printed = 0
    try:
        with open(log_to_search_in) as f:
            for line in f:
                if (re.search(AMPM_logging, line) != None):
                    dateCompared = FindRegexInLineAndConvertToDate(line, AMPM_logging, date_pat7)
                    if (dateCompared) <= date + timedelta(minutes=1) and (dateCompared) >= date - timedelta(
                            minutes=1):
                        if (first_line_was_printed == 0):
                            WriteLogName(file_to_write_to, log_to_search_in)
                            first_line_was_printed = 1
                        file_to_write_to.write(line+"\n")
                        CheckForStackTrace(log_to_search_in, line, file_to_write_to)
    except Exception as e:
        print ("error in ampm patterns logs" + str(e))


def SearchTheDateInCurrentLog(date, log_to_search_in, file_to_write_to):
    with open(log_to_search_in) as f:
        try:
            first_line = f.readline() #Our indication of what kinf og log pattern we dealing with
            if (re.search(verbose_logging_first_line_pattern, first_line) != None):
                SearchInVerboseLogs(log_to_search_in, file_to_write_to,
                                    date)
            elif (re.search(date_parser_pattern, first_line) != None):
                SearchWithDateParser(log_to_search_in, file_to_write_to, date)
            elif(re.search(date_parser_pattern2_first_line_pattern, first_line) != None):
                SearchWithDateParser2(log_to_search_in, file_to_write_to, date)
            elif (re.search(all_regular_patterns, first_line) != None):
                SearchWithRegularPatterns(log_to_search_in, file_to_write_to, date)
            elif (re.search(AMPM_logging, first_line) != None):
                SearchWithAmpmPattern(log_to_search_in, file_to_write_to, date)
            else:
                file_to_write_to.write("*******The following log didn't match any date pattern:" + os.path.basename(
                    log_to_search_in) + "*******\n")
        except Exception as e:
            print ("error in searching in log" + str(e))


def SearchTheDateInAllLogs(date, path, file_to_write_to):
    log_files = [os.path.join(path, f)
                 for path, names, files in os.walk(path)
                 for f in fnmatch.filter(files, '*.txt' or '*.log')
                 ]
    date_guests = date + timedelta(hours=1) # use in case we need to take care of time difference between guests and host
    for files in log_files:
        if (re.search(("vm0" or "vm1"), str(files))!=None): #use in case we need to take care of time difference between guests and host
            SearchTheDateInCurrentLog(date_guests, files, file_to_write_to)
        else:
            SearchTheDateInCurrentLog(date, files, file_to_write_to)


def start(logsRelatedToFailure, source, path_of_collected_logs):
    try:
        # ensure we are writing to a blank file
        with open(logsRelatedToFailure, "w") as file_to_write_to:
            file_to_write_to.write("")
            date = FindTheFailDate(file_to_write_to, source)
            SearchTheDateInCurrentLog(date, source, file_to_write_to) #search the lines that were reported in timedelta of 1 min from the fail dare in a log file, first time we call it - searching in the main test log
            SearchTheDateInAllLogs(date, path_of_collected_logs, file_to_write_to) #searching the same in the logs folder
    except Exception:
        pass

#Starting the program giving parameters in cmd
if __name__ == "__main__":
    logsRelatedToFailure = os.path.normpath(sys.argv[1])
    initial_test_log = os.path.normpath(sys.argv[2])
    path_of_collected_logs = os.path.normpath(sys.argv[3])
    start(logsRelatedToFailure, initial_test_log, path_of_collected_logs)






