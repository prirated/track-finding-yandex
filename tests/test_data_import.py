"""
Tests for importing data from root file
"""
from __future__ import print_function
import sys
import pytest
import numpy as np
sys.path.insert(0, "../modules")
from root_numpy import list_branches
import hits

# Pylint settings
# pylint: disable=redefined-outer-name

# Define the verbosity at the global scope
# test files we will use
FILES = ["test_file_a"]
# names used for import that belong together
NAMES = {}
NAMES["CDC"] = ("CDCHitTree", "CDCHit.f")
NAMES["CTH"] = ("CTHHitTree", "CTHHit.f")
# some specific test branches for when they are needed
BRANCHES = ['Track.fStartMomentum.fX',
            'Track.fStartMomentum.fY',
            'Track.fStartMomentum.fZ']

# TODO
# test get measurement
# test sort hits
# test import subset of events

# HELPER FUNCTIONS #############################################################
def filter_branches(branches):
    """
    Filter out the branches that are automatically imported
    """
    ret_val = branches
    for filter_br in ["CDCHit.fDetectedTime",
                      "CDCHit.fCharge",
                      "CDCHit.fEventNumber",
                      "CDCHit.fIsSig",
                      'CTHHit.fMCPos.fE',
                      'CTHHit.fCharge',
                      'CTHHit.fEventNumber',
                      'CTHHit.fIsSig']:
        ret_val = [brch for brch in ret_val if filter_br not in brch]
    return ret_val

# TEST BASIC IMPORT FUNCTIONS ##################################################

@pytest.fixture(params=[
    # Parameterize the array construction
    # path, geom, branches,
    (FILES[0], "CDC", 'all'),
    (FILES[0], "CTH", 'all'),
    (FILES[0], "CDC", [NAMES["CDC"][1]+branch for branch in BRANCHES]),
    (FILES[0], "CTH", [NAMES["CTH"][1]+branch for branch in BRANCHES])])
def cstrct_hits_params(request):
    """
    Parameterize the flat hit parameters
    """
    return request.param

@pytest.fixture()
def flat_hits(cstrct_hits_params):
    """
    Construct the base flat hits object
    """
    # Unpack the parameters
    file, geom, branch = cstrct_hits_params
    tree, prefix = NAMES[geom]
    root_file = file + ".root"
    # Load all the branches
    if branch == "all":
        branch = filter_branches(list_branches(root_file, treename=tree))
    # Load the file
    sample = hits.FlatHits(root_file,
                           tree=tree,
                           prefix=prefix,
                           branches=branch)
    return sample, file, geom

@pytest.fixture()
def flat_hits_and_ref(flat_hits):
    """
    Package the hits and the reference data together
    """
    # Unpack the parameters
    sample, file, geom = flat_hits
    # Check that it is the same as the first time we loaded in this data
    reference_file = file+"_"+geom+".npz"
    reference_data = np.load(reference_file)["array"]
    # Return the information
    return sample, reference_data

def test_sample_columns(flat_hits_and_ref):
    """
    Ensure the data columns are the same
    """
    # Unpack the information
    sample, reference_data = flat_hits_and_ref
    # Ensure column names are subset of reference names
    ref_columns = list(reference_data.dtype.names)
    ref_columns.sort()
    new_columns = list(sample.data.dtype.names)
    new_columns.sort()
    miss_cols = list(set(new_columns) - set(ref_columns))
    assert not miss_cols, "Columns in loaded sample are not found in "+\
        "reference sample \n{}".format("\n".join(miss_cols))

def test_sample_data(flat_hits_and_ref):
    """
    Ensure the data columns are the same
    """
    # Unpack the information
    sample, reference_data = flat_hits_and_ref
    # Ensure all the data is the same
    for col in sample.data.dtype.names:
        new_data = sample.data[col]
        ref_data = reference_data[col]
        np.testing.assert_allclose(new_data, ref_data)

# FLAT HITS SELECTED TESTS #####################################################
@pytest.fixture(params=[
    # Parameterize the array construction
    # selection
    [BRANCHES[0] + " < 0"],
    [BRANCHES[1] + " > 0"],
    [BRANCHES[1] + " > 0", BRANCHES[0] +" < 0"],
    [BRANCHES[1] + " > 0", BRANCHES[0] +" < 0", BRANCHES[2] + " > 0"],
    ["EventNumber == 1", BRANCHES[0] +" < 0"]
    ])
def cstrct_hits_params_sel(request, cstrct_hits_params):
    """
    Parameterize the flat hit parameters with selections
    """
    file, geom, branch = cstrct_hits_params
    selection = request.param
    selection = " && ".join(NAMES[geom][1]+sel for sel in selection)
    return file, geom, branch, selection

@pytest.fixture()
def flat_hits_sel(cstrct_hits_params_sel):
    """
    Construct the base flat hits object with some selections
    """
    # Unpack the parameters
    file, geom, branch, selection = cstrct_hits_params_sel
    tree, prefix = NAMES[geom]
    root_file = file + ".root"
    # Load all the branches
    if branch == "all":
        branch = filter_branches(list_branches(root_file, treename=tree))
    # Load the file
    sample = hits.FlatHits(root_file,
                           tree=tree,
                           prefix=prefix,
                           selection=selection,
                           branches=branch)
    return sample, selection

def test_flat_hits_sel(flat_hits_sel):
    """
    Test that the selections worked
    """
    sample, selection = flat_hits_sel
    # Deconstruct the selections
    sel_list = selection.split(" && ")
    sel_list = [sel.split(" ") for sel in sel_list]
    error_message = "All values must pass the relations: {}".format(selection)
    for branch, relation, value in sel_list:
        if relation == "<":
            print("Failed {} {} {}".format(branch, relation, value))
            assert np.all(sample.data[branch] < float(value)), error_message
        elif relation == ">":
            print("Failed {} {} {}".format(branch, relation, value))
            assert np.all(sample.data[branch] > float(value)), error_message
        elif relation == "==":
            print("Failed {} {} {}".format(branch, relation, value))
            assert np.all(sample.data[branch] == float(value)), error_message
        else:
            error_message = "Relation symbol {} not supported".format(relation)
            raise AssertionError(error_message)

# EMPTY BRANCH IMPORT ##########################################################

@pytest.fixture(params=[
    # Parameterize the array construction
    # empty branch name
    ["branch_a"],
    ["branch_b"],
    ["branch_a", "branch_b"]
    ])
def cstrct_hits_params_empty(request, cstrct_hits_params):
    """
    Parameterize the flat hit parameters with empty branches
    """
    file, geom, branch = cstrct_hits_params
    empty = request.param
    empty = [NAMES[geom][1]+sel for sel in empty]
    return file, geom, branch, empty

@pytest.fixture()
def flat_hits_empty(cstrct_hits_params_empty):
    """
    Construct the base flat hits object with some selections
    """
    # Unpack the parameters
    file, geom, branch, empty = cstrct_hits_params_empty
    tree, prefix = NAMES[geom]
    root_file = file + ".root"
    # Load all the branches
    if branch == "all":
        branch = filter_branches(list_branches(root_file, treename=tree))
    # Load the file
    sample = hits.FlatHits(root_file,
                           tree=tree,
                           prefix=prefix,
                           empty_branches=empty,
                           branches=branch)
    return sample, empty

def test_flat_hits_empty(flat_hits_empty):
    """
    Test that importing empty branches works fine
    """
    sample, empty = flat_hits_empty
    for empty_branch in empty:
        np.testing.assert_allclose(sample.data[empty_branch],
                                   np.zeros_like(sample.data[empty_branch]))

# TEST GETTERS #################################################################

@pytest.mark.parametrize("events, file_index", [
    (None, "a"),
    (2, "b"),
    (3, "c"),
    (np.arange(5), "d"),
    ([1, 3, 7, 10, 11], "e")])
def test_get_event(flat_hits, events, file_index):
    """
    Test if getting specific events works as it is supposed to
    """
    # Get the event data from the file
    sample, file, geom = flat_hits
    event_data = sample.get_events(events)
    # Get the reference file
    ref_file = file + "_" + geom + "_eventdata.npz"
    ref_data = np.load(ref_file)[file_index]
    for branch in event_data.dtype.names:
        np.testing.assert_allclose(ref_data[branch], event_data[branch])
# GENERATE THE REFERENCE
#    evts = [None, 2,3,list(range(5)),[1, 3, 7, 10, 11]]
#    if len(list(sample.data.dtype.names)) > 10:
#        np.savez_compressed(ref_file,
#                            a=sample.get_events(evts[0]),
#                            b=sample.get_events(evts[1]),
#                            c=sample.get_events(evts[2]),
#                            d=sample.get_events(evts[3]),
#                            e=sample.get_events(evts[4]))

# TEST FILTERS  ################################################################

def check_filter(filtered_hits, variable, values, greater, less, invert):
    """
    Helper function for filter tests
    """
    # Ensure there are some events left
    assert len(filtered_hits) != 0, "Filter has removed all hits!"+\
            " This has resulted in a trivial check"
    # Ensure they pass all the filter requirements
    err = "Sample filtered on variable {} ".format(variable)
    if values is not None:
        test = np.all(np.in1d(filtered_hits[variable], values))
        if invert:
            test = not test
        assert test, \
            err + "did not filter by values {} correctly".format(values)+\
            " {}".format(filtered_hits[variable])

    if greater is not None:
        test = np.all(filtered_hits[variable] > greater)
        if invert:
            test = not test
        assert test, \
            err + "did not filter by 'greater than' {} correctly".format(greater)+\
            " {}".format(filtered_hits[variable])

    if less is not None:
        test = np.all(filtered_hits[variable] < less)
        if invert:
            test = not test
        assert test, \
            err + "did not filter by 'greater than' {} correctly".format(less)+\
            " {}".format(filtered_hits[variable])

@pytest.fixture(params=[
    #variable,      values,       greater, less, invert
    (BRANCHES[0],   None,         0,       None, False),
    (BRANCHES[0],   None,         None,    0,    False),
    (BRANCHES[0],   None,         None,    0,    True),
    ("event_index", np.arange(5), None,    None, False)
    ])
def filter_params(request):
    return request.param

def test_filtered_hits(flat_hits, filter_params):
    """
    Keep the hits satisfying this criteria
    """
    # Unpack the arguments
    sample, _, geom = flat_hits
    variable, values, greater, less, invert = filter_params
    variable = NAMES[geom][1] + variable
    # Get the relevant hits to keep
    if values is not None:
        print(sample.data[variable])
        print(values)
    filtered_hits = sample.filter_hits(variable, these_hits=None,
                                       values=values,
                                       greater_than=greater,
                                       less_than=less,
                                       invert=invert)
    check_filter(filtered_hits, variable, values, greater, less, invert)

def test_trim_hits(flat_hits, filter_params):
    """
    Keep the hits satisfying this criteria
    """
    # Unpack the arguments
    sample, _, geom = flat_hits
    variable, values, greater, less, invert = filter_params
    variable = NAMES[geom][1] + variable
    # Get the relevant hits to keep
    sample.trim_hits(variable,
                     values=values,
                     greater_than=greater,
                     less_than=less,
                     invert=invert)
    check_filter(sample.data, variable, values, greater, less, invert)