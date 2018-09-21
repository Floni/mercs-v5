import numpy as np
import warnings

from .encoding import codes_to_query

from .debug import debug_print
VERBOSITY = 0


def collect_and_verify_clf_classlabels(m_list, m_codes):
    """
    Collect all the classlabels

    Parameters
    ----------
    m_list: list, shape (nb_models,)
        List of all the component models
    m_codes:
        List of all the codes of the MERCS model

    Returns
    -------

    """

    _, m_targ, _ = codes_to_query(m_codes)

    nb_atts = len(m_codes[0])
    clf_labels = initialize_classlabels(nb_atts)

    for m_idx, m in enumerate(m_list):
        # Collect the classlabels of one model
        nb_targ = len(m_targ[m_idx])
        m_classlabels = collect_classlabels(m)

        # Verify all the classlabels
        clf_labels = update_clf_labels(clf_labels, m_classlabels, m_targ[m_idx])

    return clf_labels


def collect_classlabels(m):
    """
    Collect all the classlabels of a given model m.

    Parameters
    ----------
    m: {sklearn, composite model}
        The model under consideration

    Returns
    -------

    """

    if hasattr(m, 'classes_'):
        if isinstance(m.classes_, np.ndarray):
            # Single-target sklearn output
            m_classlabels = [m.classes_]
        else:
            assert isinstance(m.classes_, list)
            m_classlabels = m.classes_
    else:
        # If no classlabels are present, we assume a fully numerical model
        m_classlabels = initialize_classlabels(m.n_outputs_, mode='numeric')

    return m_classlabels


def update_clf_labels(clf_labels, m_classlabels, m_targ):
    """
    Update the classlabels.

    Update the classlabels known to the MERCS system, based on
    potentially new information on classlabels from a new component model.

    Parameters
    ----------
    clf_labels: list, shape (nb_atts, (nb_classlabels_att,))
        List of all classlabels known to the MERCS system
    m_classlabels: list, shape (nb_targ_atts_mod, (nb_classlabels_att,))
        List of all the classlabels known to the individual model
    m_targ
        List of all targets of the individual model. These are essential to
        identify about which attributes m_classlabels is providing information!

    Returns
    -------

    """
    # TODO: Deal with numeric in a smoother way

    for t_idx, t in enumerate(m_targ):

        old_labels = clf_labels[t]          # Classlabels known to MERCS
        new_labels = m_classlabels[t_idx]   # Classlabels known the model m

        msg = "New_labels are: {}\n" \
              "Type new_labels is: {}\n".format(new_labels, type(new_labels))
        debug_print(msg, V=VERBOSITY, warn=True)

        msg = "Old_labels are: {}\n" \
              "Type old_labels is: {}\n".format(old_labels, type(old_labels))
        debug_print(msg, V=VERBOSITY, warn=True)

        assert isinstance(old_labels, (list, np.ndarray))
        assert isinstance(new_labels, (list, np.ndarray))

        if isinstance(old_labels, list):
            if old_labels == ['default']:
                # If the default value of [0] is still there, update current
                clf_labels[t] = new_labels
            elif old_labels == ['numeric']:
                # If MERCS thought attribute t was numeric, the new model must agree!
                assert new_labels == ['numeric']
            else:
                msg = "type(old_labels) is list, but not the default value nor the default value for a numeric attribute.\n" \
                      "These are the only two allowed cases for an entry in clf_labels to be a list and not np.ndarray," \
                      "so something is wrong."
                raise TypeError(msg)
        elif isinstance(old_labels, np.ndarray):
            # Join current m_classlabels with those already present
            classlabels_list = [old_labels, new_labels]
            clf_labels[t] = join_classlabels(classlabels_list)
        else:
            msg = """
            old_labels (=clf_labels[t]) can only be a list or np.ndarray.\n
            A list can only occur in two case: \n
            \t 1) Default entry: [0] \n
            \t 2) Numeric dummy entry: ['numeric]\n\n
            """
            raise TypeError(msg)

    return clf_labels


def join_classlabels(classlabels_list):
    """
    Get the union of the provided classlabels

    This is crucial whenever models are trained on different subsets of the
    data_csv, and have other ideas about what the classlabels are.
    """

    all_classes = np.concatenate(classlabels_list)

    result = np.array(list(set(all_classes)))
    result.sort()

    return result


def initialize_classlabels(nb_atts, mode='default'):

    if mode in {'default'}:
        classlabels = [['default'] for i in range(nb_atts)]
    elif mode in {'numeric'}:
        classlabels = [['numeric'] for i in range(nb_atts)]
    else:
        msg = "Did not recognize mode: {}. Assuming 'default'".format(mode)
        warnings.warn(msg)
        classlabels = initialize_classlabels(nb_atts, mode='default')

    return classlabels