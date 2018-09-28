import numpy as np

from ..utils.encoding import codes_to_query, encode_attribute

from ..utils.debug import debug_print
VERBOSITY = 0


# Core
def mi_pred_algo(m_codes, q_codes):
    """
    MI-prediction algorithm

    The most basic prediction algorithm, selects all models that share
    at least a target attribute with the query at hand, and select those,
    regardless of their descriptive attributes being available or not.

    Parameters
    ----------
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.
    q_codes: np.ndarray, shape (nb_queries, nb_atts)
        Two-dimensional np.ndarray where each row encodes a query.

    Returns
    -------
    mas: np.ndarray, shape (nb_queries, nb_models)
        Model Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the model activation strategy for a query i. Each entry in such
        a row refers to a certain model, and encodes when it may be activated.
    aas: np.ndarray, shape (nb_queries, nb_atts)
        Attribute Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the attribute activation strategy for a query i. Each entry in
        such a row refers to a certain attribute, and encodes when it may be
        activated.

    """

    assert isinstance(m_codes, np.ndarray)
    assert isinstance(q_codes, np.ndarray)
    assert m_codes.shape[1] == q_codes.shape[1]

    # Preliminaries
    nb_mods, nb_atts, nb_qrys, m_desc, m_targ, q_desc, q_targ = _pred_prelims(m_codes,
                                                                              q_codes)
    mas, aas = _init_mas_aas_np(nb_mods, nb_atts, nb_qrys)

    for q_idx in range(nb_qrys):
        aas[q_idx], mas[q_idx] = _mi_pred_algo_single_qry(aas[q_idx],
                                                          mas[q_idx],
                                                          q_desc[q_idx],
                                                          q_targ[q_idx],
                                                          m_codes)

    return mas, aas


def _mi_pred_algo_single_qry(aas, mas, q_desc, q_targ, m_codes):
    """
    MI-prediction algorithm for a single query

    Parameters
    ----------
    aas: np.ndarray, shape (nb_attributes,)
        Attribute Activation Strategy for a single query.
    aas: np.ndarray, shape (nb_models,)
        Model Activation Strategy for a single query.
    q_desc: list, shape (nb_descriptive_atts_query, )
        List of the indices of the descriptive attributes of this query
    q_targ: list, shape (nb_target_atts_query)
        List of the indices of the target attributes of this query
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.

    Returns
    -------
    aas: np.ndarray, shape (nb_atts, )
        Attribute Activation Strategy for single query.
        One-dimensional np.ndarray, where an entry i encodes at which step
        attribute i may be activated.
    mas: np.ndarray, shape (nb_models)
        Model Activation Strategy for single query.
        One-dimensional np.ndarray, where an entry j encodes at which step
        model j may be activated.
    """
    assert isinstance(aas, np.ndarray)
    assert isinstance(mas, np.ndarray)
    assert len(mas.shape) == len(aas.shape) == 1
    # Prelims
    aas[q_desc] = 0

    # Model activation
    relevant_models = np.where(m_codes[:, q_targ] == 1)[0]  # Models sharing target with queries
    mas[relevant_models] = 1

    # Att. activation
    aas[q_targ] = 1  # Does not depend on model activation strategy

    return aas, mas


def ma_pred_algo(m_codes, q_codes, settings):
    """
    MA-prediction algorithm

    Parameters
    ----------
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.
    q_codes: np.ndarray, shape (nb_queries, nb_atts)
        Two-dimensional np.ndarray where each row encodes a query.
    settings

    Returns
    -------
    mas: np.ndarray, shape (nb_queries, nb_models)
        Model Activation Strategy.
        Two-dimensional np.ndarray where row i encodes the model activation
        strategy for a query i. Each entry in such a row refers to a certain
        model, and encodes at which step it may be activated.
    aas: np.ndarray, shape (nb_queries, nb_atts)
        Attribute Activation Strategy.
        Two-dimensional np.ndarray where row i encodes the attribute activation
        strategy for a query i. Each entry in such a row refers to a certain
        attribute, and encodes at which step it may be activated.
    """

    initial_threshold = settings['param']
    step_size = settings['its']
    assert isinstance(initial_threshold, (int, float))
    assert isinstance(step_size, float)
    assert 0.0 < initial_threshold <= 1.0
    assert 0.0 < step_size < 1.0

    # Preliminaries
    nb_models, nb_atts, nb_qrys, m_desc, m_targ, q_desc, q_targ = _pred_prelims(m_codes,
                                                                                q_codes)
    mas, aas = _init_mas_aas_np(nb_models, nb_atts, nb_qrys)
    thresholds = np.arange(initial_threshold, -1, -step_size)

    msg = """
    ma_pred_algo\n
    initial thresholds:\t{}\n
    step_size:\t{}\n
    thresholds:\t {}\n
    """.format(initial_threshold, step_size, thresholds)
    debug_print(msg, V=VERBOSITY)

    # Building codes
    for q_idx in range(nb_qrys):
        aas[q_idx], mas[q_idx] = _ma_pred_algo_single_qry(aas[q_idx],
                                                          mas[q_idx],
                                                          q_desc[q_idx],
                                                          q_targ[q_idx],
                                                          m_codes,
                                                          m_desc,
                                                          thresholds)

    return mas, aas


def _ma_pred_algo_single_qry(aas,
                             mas,
                             q_desc,
                             q_targ,
                             m_codes,
                             m_desc,
                             thresholds):
    """
    MA-prediction algorithm for a single query

    Parameters
    ----------
    aas: np.ndarray, shape (nb_attributes,)
        Attribute Activation Strategy for a single query.
    aas: np.ndarray, shape (nb_models,)
        Model Activation Strategy for a single query.
    q_desc: list, shape (nb_descriptive_atts_query, )
        List of the indices of the descriptive attributes of this query
    q_targ: list, shape (nb_target_atts_query)
        List of the indices of the target attributes of this query
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.
    m_desc: list, shape (nb_models, nb_desc_atts_model)
        List of lists. An entry i is the list of the indices of descriptive
        attributes of model i.
    thresholds: np.ndarray, shape (nb_steps, )
        Array of all the threshold values we might explore.

    Returns
    -------
    aas: np.ndarray, shape (nb_atts, )
        Attribute Activation Strategy for single query.
        One-dimensional np.ndarray, where an entry i encodes at which step
        attribute i may be activated.
    mas: np.ndarray, shape (nb_models)
        Model Activation Strategy for single query.
        One-dimensional np.ndarray, where an entry j encodes at which step
        model j may be activated.
    """

    assert isinstance(aas, np.ndarray)
    assert isinstance(mas, np.ndarray)
    assert len(mas.shape) == len(aas.shape) == 1

    # Single-target case
    if len(q_targ) == 1:
        # Prelims
        nb_models = mas.shape[0]

        # Initialization
        targ_encoding = encode_attribute(1,[0],[1])
        avl_atts_idx = q_desc
        avl_mods_idx = np.where(m_codes[:, q_targ] == targ_encoding)[0]  # Models sharing target attribute with query

        aas[avl_atts_idx] = 0

        # Convert to binary arrays
        avl_atts = aas > -1

        # Att. activation
        aas[q_targ] = 1

        # Model activation
        def mod_appr_score(avl_atts, mod_desc):
            """Custom appreciation score for this algorithm"""
            return np.sum(avl_atts.take(mod_desc)) / len(mod_desc)

        mod_appr_scores = [mod_appr_score(avl_atts, m_desc[m_idx])
                           if m_idx in avl_mods_idx else -np.inf
                           for m_idx in range(nb_models)]

        step = 1
        for thr in thresholds:
            mas = [step
                   if mod_appr_scores[m_idx] > thr else v
                   for m_idx, v in enumerate(mas)]

            mas = np.array(mas, dtype=int)

            if _ma_mafi_stopping_condition(mas, m_codes, q_targ):
                break

    # Multi-target case
    elif len(q_targ) > 1:
        for t in q_targ:
            aas_single_t, mas_single_t = _ma_pred_algo_single_qry(aas,
                                                                  mas,
                                                                  q_desc,
                                                                  [t],
                                                                  m_codes,
                                                                  m_desc,
                                                                  thresholds)

            mas[mas_single_t > 0] = 1   # Each target selects some models

        aas = aas_single_t              # This is the same for each target t
    else:
        msg = """
        q_targ: {}\n
        This is not a good target set for a query.
        """.format(q_targ)
        raise ValueError(msg)

    return aas, mas


def mafi_pred_algo(m_codes, q_codes, settings):
    """

    Parameters
    ----------
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.
    q_codes: np.ndarray, shape (nb_queries, nb_atts)
        Two-dimensional np.ndarray where each row encodes a query.

    Returns
    -------
    mas: np.ndarray, shape (nb_queries, nb_models)
        Model Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the model activation strategy for a query i. Each entry in such
        a row refers to a certain model, and encodes when it may be activated.
    aas: np.ndarray, shape (nb_queries, nb_atts)
        Attribute Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the attribute activation strategy for a query i. Each entry in
        such a row refers to a certain attribute, and encodes when it may be
        activated.

    """

    initial_threshold = settings['param']
    step_size = settings['its']
    assert isinstance(initial_threshold, (int, float))
    assert isinstance(step_size, float)
    assert 0.0 < initial_threshold <= 1.0
    assert 0.0 < step_size < 1.0

    # Preliminaries
    nb_models, nb_atts, nb_queries, m_desc, m_targ, q_desc, q_targ = _pred_prelims(m_codes,
                                                                                   q_codes)
    mas, aas = _init_mas_aas(nb_models, nb_atts, nb_queries)

    thresholds = np.arange(initial_threshold, -1, -step_size)
    FI = settings['FI']

    # Building mas & aas codes
    for q_idx, q_code in enumerate(q_codes):

        msg = "This is q_targ[q_idx]: {}".format(q_targ[q_idx])
        debug_print(msg, V=VERBOSITY, warn=True)

        for t in q_targ[q_idx]:
            msg = "This is t, the target which we consider: {}".format(t)
            debug_print(msg, V=VERBOSITY, warn=True)

            aas_target_t, mas_target_t = _mafi_mas_aas(aas[q_idx],
                                                       mas[q_idx],
                                                       q_desc[q_idx],
                                                       [t],
                                                       m_codes,
                                                       FI,
                                                       thresholds)

            msg = "This is mas_target_t: {}".format(mas_target_t)
            debug_print(msg, V=VERBOSITY, warn=True)

            mas[q_idx][mas_target_t > 0] = 1  # Each target selects some models
            aas[q_idx] = aas_target_t  # This is unchanged.

            msg = "This is mas[q_idx]: {}".format(mas[q_idx])
            debug_print(msg, V=VERBOSITY, warn=True)

    return np.array(mas), np.array(aas)


def it_pred_algo(m_codes, q_codes, settings):
    """

    Parameters
    ----------
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.
    q_codes: np.ndarray, shape (nb_queries, nb_atts)
        Two-dimensional np.ndarray where each row encodes a query.

    Returns
    -------
    mas: np.ndarray, shape (nb_queries, nb_models)
        Model Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the model activation strategy for a query i. Each entry in such
        a row refers to a certain model, and encodes when it may be activated.
    aas: np.ndarray, shape (nb_queries, nb_atts)
        Attribute Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the attribute activation strategy for a query i. Each entry in
        such a row refers to a certain attribute, and encodes when it may be
        activated.

    """

    # Preliminaries
    nb_models, nb_atts, nb_queries, m_desc, m_targ, q_desc, q_targ = _pred_prelims(m_codes,
                                                                                   q_codes)
    mas, aas = _init_mas_aas(nb_models, nb_atts, nb_queries)

    # Collecting parameters from s
    init_threshold = 1
    step_size = settings['param']
    max_layers = settings['its']
    assert isinstance(max_layers, int)
    assert 0 < max_layers
    assert isinstance(step_size, float)
    assert 0.0 < step_size < 1.0

    FI = settings['FI']

    # Building codes
    for q_idx, q_code in enumerate(q_codes):

        # Prelims
        aas[q_idx][q_desc[q_idx]] = 0

        thresholds = iter(np.arange(init_threshold, -1, -step_size))  # Set thresholds
        done = False
        step = 1
        while not done:
            avl_mods = mas[q_idx] > 0
            avl_atts = aas[q_idx] > -1

            # Model activation
            mod_appr_scores = [np.dot(avl_atts, FI[m_idx])
                               if (avl_mods[m_idx] == 0) else -1
                               for m_idx in range(nb_models)]  # Only score non-available ones!

            mod_progress = False
            while not mod_progress:
                thr = next(thresholds)

                msg = """
                Threshold:\t{}\n
                """.format(thr)
                debug_print(msg, V=VERBOSITY)

                mas[q_idx] = [step if (mod_appr_scores[m_idx] > thr) else v
                              for m_idx, v
                              in enumerate(mas[q_idx])]  # Appropriate enough models
                mas[q_idx] = np.array(mas[q_idx])
                mod_progress = np.sum(mas[q_idx] == step) >= 1

            # Attr. activation
            msg = """
            Query index:\t{}\n
            Model act codes:\t{}\n
            """.format(q_idx, mas[q_idx])
            debug_print(msg, V=VERBOSITY)

            avl_mods = np.array(mas[q_idx]) > 0  # Update required

            msg = """
            Available models:\t{}\n
            """.format(avl_mods)
            debug_print(msg, V=VERBOSITY)

            avl_mod_codes = m_codes[avl_mods]

            att_appr_scores = [np.sum(avl_mod_codes[:, a_ind] == 1)
                               if (avl_atts[a_ind] == 0) else -1
                               for a_ind in range(nb_atts)]  # Only score non-available ones!

            msg = """
            att_appr_scores:\t{}\n
            """.format(att_appr_scores)
            debug_print(msg, V=VERBOSITY)

            aas[q_idx] = [step if (att_appr_scores[a_ind] > 0) else v
                          for a_ind, v
                          in enumerate(aas[q_idx])]
            aas[q_idx] = np.array(aas[q_idx])

            # Loop technics
            att_progress = np.sum(aas[q_idx] == step)
            if att_progress > 0 and step < max_layers:
                step += 1
                thresholds = iter(np.arange(init_threshold, -1, -step_size))  # Reset thresholds

            done = (np.sum(aas[q_idx][q_targ[q_idx]] < 0) == 0)

    return np.array(mas), np.array(aas)


def rw_pred_algo(m_codes, q_codes, settings):
    """
    Random Walk prediction algo.

    Generate one random walk in the random forest.

    Parameters
    ----------
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.
    q_codes: np.ndarray, shape (nb_queries, nb_atts)
        Two-dimensional np.ndarray where each row encodes a query.

    Returns
    -------
    mas: np.ndarray, shape (nb_queries, nb_models)
        Model Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the model activation strategy for a query i. Each entry in such
        a row refers to a certain model, and encodes when it may be activated.
    aas: np.ndarray, shape (nb_queries, nb_atts)
        Attribute Activation Strategy. Two-dimensional np.ndarray where row i
        encodes the attribute activation strategy for a query i. Each entry in
        such a row refers to a certain attribute, and encodes when it may be
        activated.

    """

    # Preliminaries
    nb_models, nb_atts, nb_queries, m_desc, m_targ, q_desc, q_targ = _pred_prelims(m_codes,
                                                                                   q_codes)
    mas, aas = _init_mas_aas(nb_models, nb_atts, nb_queries)

    # Building codes
    for q_idx, q_code in enumerate(q_codes):
        mas[q_idx], aas[q_idx] = generate_chain(m_codes,
                                                q_desc[q_idx],
                                                q_targ[q_idx],
                                                settings)

    return np.array(mas), np.array(aas)


# Helpers
def _pred_prelims(m_codes, q_codes):
    """
    Extract some useful quantities every prediction strategy needs

    Parameters
    ----------
    m_codes: np.ndarray, shape (nb_models, nb_atts)
        Two-dimensional np.ndarray where each row encodes a model of the MERCS
        ensemble.
    q_codes: np.ndarray, shape (nb_queries, nb_atts)
        Two-dimensional np.ndarray where each row encodes a query.

    Returns
    -------

    """

    assert isinstance(m_codes, np.ndarray)
    assert isinstance(q_codes, np.ndarray)

    nb_models, nb_atts = m_codes.shape
    nb_queries = q_codes.shape[0]

    m_desc, m_targ, _ = codes_to_query(m_codes)
    q_desc, q_targ, _ = codes_to_query(q_codes)

    return nb_models, nb_atts, nb_queries, m_desc, m_targ, q_desc, q_targ


def generate_chain(m_codes, q_desc, q_targ, settings):
    # Choose chain length
    assert isinstance(settings['its'], int)
    max_size = settings['its'] + 1
    chain_size = np.random.randint(1, max_size)
    steps = np.arange(chain_size, 0, -1, dtype=int)

    FI = settings['FI']

    # Initializations
    nb_models = len(m_codes)
    nb_atts = len(m_codes[0])

    mas = np.full(nb_models, 0, dtype=np.int)
    aas = np.full(nb_atts, -1, dtype=np.int)
    aas[q_desc] = 0

    for i, step in enumerate(steps):
        # Select possible targets
        if i == 0:
            potential_targ = q_targ
        else:
            assert step >= 1
            next_mods = (mas == step + 1)
            potential_targ = get_atts(m_codes, next_mods, 0)

        potential_targ = np.array([e for e in potential_targ
                                   if aas[e] == -1])  # Predict only unknown atts
        if len(potential_targ) == 0: break  # Nothing left to contribute

        # Select potential models (= model which predicts a potential target)
        potential_mods = np.array([m_idx for m_idx, e in enumerate(mas)
                                   if (e == 0)
                                   if (np.sum(m_codes[m_idx, potential_targ] == 1) > 0)])

        # NEW ADDITION I DONT KNOW IF THIS IS OKAY
        if len(potential_mods) == 0: break  # Nothing left to contribute

        # Select model
        available_atts = [1 if (-1 < aas[i] < step) else 0 for i in range(len(aas))]
        mod_appr_scores = [np.dot(available_atts, FI[m_idx]) for m_idx in potential_mods]

        curr_mod_idx = potential_mods[pick_random_models_from_appr_score(mod_appr_scores, n=1) > 0]

        mas[curr_mod_idx] = step

        # Select target
        curr_mods_targ = get_atts(m_codes, curr_mod_idx, 1)
        relv_targ_idx = np.intersect1d(potential_targ, curr_mods_targ)

        aas[relv_targ_idx] = step

    if not np.max(mas) > 0:
        contents = (i,
                    step,
                    potential_targ,
                    aas,
                    m_codes,
                    type(m_codes),
                    steps,
                    chain_size,
                    q_desc,
                    q_targ)
        msg = """
        i, step: \t{}, {}\n
        potential targ: \t {}\n
        aas: \t{}\n
        m_codes: \t{}\n
        type(m_codes): \t {}\n
        steps: \t{}\n
        chain_size \t{}\n
        q_desc \t{}\n
        q_targ \t{}\n
        """.format(*contents)
        debug_print(msg, V=VERBOSITY)

    assert np.max(aas) == np.max(mas)
    assert np.max(mas) > 0
    mas, aas = recode_strat(mas, aas)

    return mas, aas


def _mafi_mas_aas(aas, mas, q_desc, q_targ, m_codes, FI, thresholds):
    """


    Parameters
    ----------
    aas: np.ndarray, shape (nb_attributes,)
        Single aas, initialized
    mas: np.ndarray, shape (nb_models,)
        Single mas, initialized
    q_desc: list, shape (nb_desc_atts_query)
        Descriptive attributes of query under consideration
    q_targ: list, shape (nb_desc_atts_query)
        Target attributes of query under consideration
    m_codes: np.ndarray, shape (nb_models, nb_attributes)
        Codes of all the models
    FI
        FI of all the models

    Returns
    -------
    aas: np.ndarray, shape (nb_attributes,)

    mas: np.ndarray, shape (nb_models,)

    """
    # Prelims
    nb_models = mas.shape[0]
    aas[q_desc] = 0

    relevant_models = np.where(m_codes[:, q_targ] == 1)[0]  # Models that share at least a single target with the query
    mas[relevant_models] = 1

    avl_mods = mas > 0  # Available models share a target with queries
    avl_atts = aas > -1

    # Att. activation
    aas[q_targ] = 1  # Does not depend on model activation strategy

    # Model activation
    def appr_score(avl_atts, mod_FI):
        assert avl_atts.shape == mod_FI.shape
        return np.dot(avl_atts, mod_FI)

    mod_appr_scores = [appr_score(avl_atts, FI[m_ind])
                       if (avl_mods[m_ind] == 1) else -1
                       for m_ind in range(nb_models)]  # Only available models get considered here

    for thr in thresholds:
        mas = [1 if (mod_appr_scores[m_ind] > thr) else 0
               for m_ind in range(nb_models)]  # Binary selection of all appropriate enough models
        mas = np.array(mas)

        if _ma_mafi_stopping_condition(mas, m_codes, q_targ):
            break

    return aas, mas


def _ma_mafi_stopping_condition(mas, m_codes, q_targ):
    """

    First, we generate q_targ_attributes_in_selected_models,
    which is a subset of m_codes. Containing only those models who are
    activated, and only the q_targ attributes. The idea is that every column
    should at least have a target-code!

    Parameters
    ----------
    mas
    m_codes
    q_targ: list

    Returns
    -------

    """
    q_targ_attributes_in_selected_models = m_codes[mas == 1, :][:, q_targ]

    target_encoding = encode_attribute(1, [0], [1])
    check = np.where(q_targ_attributes_in_selected_models == target_encoding)
    q_targ_ok = np.unique(check[1])
    return len(q_targ_ok) == len(q_targ)


def _init_mas_aas(nb_models, nb_atts, nb_queries):
    """
    Initialize the mas and aas arrays.

    Parameters
    ----------
    nb_models: int
        Total number of models in the MERCS model
    nb_atts: int
        Total number of attributes in the MERCS model
    nb_queries: int
        Total number of queries that needs to be answered.

    Returns
    -------
    mas: [np.ndarray], shape (nb_queries, (nb_models,))
        E.g.:
            [array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
             array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])]
    aas: [np.ndarray], shape (nb_queries, (nb_atts,))
        E.g.:
            [array([-1, -1, -1]),
             array([-1, -1, -1])]
    """
    assert isinstance(nb_models, int)
    assert isinstance(nb_atts, int)
    assert isinstance(nb_queries, int)

    mas = [np.full(nb_models, 0, dtype=np.int) for j in range(nb_queries)]
    aas = [np.full(nb_atts, -1, dtype=np.int) for j in range(nb_queries)]
    return mas, aas


def _init_mas_aas_np(nb_models, nb_atts, nb_queries):
    """
    Initialize the mas and aas arrays.

    Difference with the above is that this outputs full numpy arrays.

    Parameters
    ----------
    nb_models: int
        Total number of models in the MERCS model
    nb_atts: int
        Total number of attributes in the MERCS model
    nb_queries: int
        Total number of queries that needs to be answered.

    Returns
    -------
    mas: np.ndarray, shape (nb_queries, nb_models)
        E.g.:
            np.array([[0,0,0],
                      [0,0,0]])
    aas: np.ndarray, shape (nb_queries, nb_atts)
        E.g.:
            np.array([[-1,-1,-1,-1],
                      [-1,-1,-1,-1]])
    """

    assert isinstance(nb_models, int)
    assert isinstance(nb_atts, int)
    assert isinstance(nb_queries, int)

    mas = np.full((nb_queries, nb_models), 0, dtype=np.int)
    aas = np.full((nb_queries, nb_atts), -1, dtype=np.int)
    return mas, aas





def prune_strat(m_codes, q_code, mas, aas):
    """
    Prune the last step of the activation strategies.

    :param m_codes:         model codes
    :param q_code:          code of the queries
    :param mas:             Model Activation Strategy
    :param aas:             Attribute Activation Strategy
    :return:
    """

    step = np.max(aas)
    aas = np.array([e if ((e != step) | (q_code[i] == 1)) else 0
                    for i, e in enumerate(aas)])

    act_atts = (aas == step)
    mas = [e if ((e != step) | (np.sum(m_codes[i][act_atts] == 1) > 0))
           else 0
           for i, e in enumerate(mas)]

    return np.array(mas), np.array(aas)


def full_prune_strat(m_codes, q_code, mas, aas):
    """
    Prune the last step of the activation strategies.

    :param m_codes:         model codes
    :param q_code:          code of the queries
    :param mas:             Model Activation Strategy
    :param aas:             Attribute Activation Strategy
    :return:
    """

    max_step = np.max(aas)

    for i in range(max_step):
        step = max_step - i

        if step == max_step:
            aas = np.array([e if ((e != step) | (q_code[i] == 1))
                            else 0 for i, e in enumerate(aas)])
        else:
            next_act_mods = (mas > step)

            msg = """
            Next act mods:\t{}\n
            """.format(next_act_mods)
            debug_print(msg, V=VERBOSITY)

            aas = np.array(
                [e if ((e != step) | (np.sum(m_codes[next_act_mods, i] == 0) > 0) | (q_code[i] == 1))
                 else 0 for i, e in enumerate(aas)])

        act_atts = (aas >= step)
        mas = [e if ((e != step) | (np.sum(m_codes[i][act_atts] == 1) > 0))
               else 0 for i, e in enumerate(mas)]

    # Recode strategies
    mas, aas = recode_strat(mas, aas)

    return mas, aas


def recode_strat(mas, aas):
    """
    Avoid gaps in strategy, and make sure that it starts from one.

    :param mas:     Model Activation Strategy
    :param aas:     Attribute Activation Strategy
    :return:
    """

    # Recode the arrays, some layers might disappear completely!
    uniq_mas, uniq_aas = np.unique(mas), np.unique(aas)
    uniq_mas = np.array([e for e in uniq_mas if e > 0])
    uniq_aas = np.array([e for e in uniq_aas if e > 0])
    mas = np.array([np.where(uniq_mas == e)[0][0] + 1 if e > 0 else e for e in mas])
    aas = np.array([np.where(uniq_aas == e)[0][0] + 1 if e > 0 else e for e in aas])  # -1 for unknown targets

    return mas, aas


def get_atts(m_codes, m_idx, role=0):
    """
    Get the attributes that fulfill a certain role in the selected models.

    The role refers to the m_codes, i.e. 0 = desc, -1 = missing, 1 = target.
    """

    all_atts = np.where(m_codes[m_idx, :] == role)[1]  # Where all the attributes with 'role' are
    unique_atts = np.unique(all_atts)
    return unique_atts


def pick_random_models_from_appr_score(mod_appr_scores, n=1):
    norm = np.linalg.norm(mod_appr_scores, 1)
    if norm > 0:
        mod_appr_scores = mod_appr_scores / norm
    else:
        # If you cannot be right, be arbritrary
        mod_appr_scores = [1 / len(mod_appr_scores) for i in mod_appr_scores]

    return np.random.multinomial(n, mod_appr_scores, size=1)[0]
