import copy
import numpy as np
from scipy import linalg

from .constants import FIFF
from .open import fiff_open
from .tree import dir_tree_find
from .channels import read_bad_channels
from .tag import find_tag, has_tag
from .source_space import read_source_spaces


def transpose_named_matrix(mat):
    """Transpose mat inplace (no copy)
    """
    mat['nrow'] = mat['ncol']
    mat['ncol'] = mat['nrow']
    mat['row_names'] = mat['col_names']
    mat['col_names'] = mat['row_names']
    mat['data'] = mat['data'].T
    return mat


def block_diag(A, n):
    """
    %
    %   function bd = mne_block_diag(A,n)
    %
    %   Make or extract a sparse block diagonal matrix
    % 
    %   If A is not sparse, then returns a sparse block diagonal "bd", diagonalized from the
    %   elements in "A".
    %   "A" is ma x na, comprising bdn=(na/"n") blocks of submatrices.
    %   Each submatrix is ma x "n", and these submatrices are
    %   placed down the diagonal of the matrix.
    %
    %   If A is already sparse, then the operation is reversed, yielding a block
    %   row matrix, where each set of n columns corresponds to a block element
    %   from the block diagonal.
    %
    %   Routine uses NO for-loops for speed considerations.
    """
    from scipy import sparse

    import pdb; pdb.set_trace()

    # if not sparse.issparse(A): # then make block sparse
    #     ma, na = A.shape
    #     bdn = na / float(n) # number of submatrices
    # 
    #     if bdn > int(bdn):
    #         raise ValueError, 'Width of matrix must be even multiple of n'
    # 
    #     tmp = reshape([1:(ma*bdn)]',ma,bdn);
    #     i = zeros(ma*n,bdn);
    #     for iblock = 1:n:
    #         i((iblock-1)*ma+[1:ma],:) = tmp
    # 
    #     i = i.ravel() # row indices foreach sparse bd
    # 
    #     j = [1:na];
    #     j = j(ones(ma,1),:);
    #     j = j(:) # column indices foreach sparse bd
    # 
    #     bd = sparse(i,j,A(:));
    # else: # already is sparse, unblock it
    #     [mA,na] = size(A);        % matrix always has na columns
    #     % how many entries in the first column?
    #     bdn = na/n;           % number of blocks
    #     ma = mA/bdn;          % rows in first block
    # 
    #     % blocks may themselves contain zero entries.  Build indexing as above
    #     tmp = reshape([1:(ma*bdn)]',ma,bdn);
    #     i = zeros(ma*n,bdn);
    #     for iblock = 1:n,
    #     i((iblock-1)*ma+[1:ma],:) = tmp;
    #     end  
    # 
    #     i = i(:);             % row indices foreach sparse bd
    # 
    # 
    #     j = [0:mA:(mA*(na-1))];
    #     j = j(ones(ma,1),:);
    #     j = j.ravel()
    # 
    #     i += j
    # 
    #     bd = full(A(i));  % column vector
    #     bd = reshape(bd,ma,na);   % full matrix

    return bd


def transform_source_space_to(src, dest, trans):
    """
    %
    % [res] = mne_transform_source_space_to(src,dest,trans)
    %
    % Transform source space data to the desired coordinate system
    %
    % fname      - The name of the file
    % include    - Include these channels (optional)
    % exclude    - Exclude these channels (optional)
    %
    """

    if src['coord_frame'] == dest:
        res = src
        return res

    if trans['to'] == src['coord_frame'] and trans['from_'] == dest:
        trans = invert_transform(trans)
    elif trans['from_'] != src['coord_frame'] or trans['to'] != dest:
        raise ValueError, 'Cannot transform the source space using this coordinate transformation'

    t = trans['trans'][:3,:]
    res = src
    res['coord_frame'] = dest

    res['rr'] = np.dot(np.c_[res['rr'], np.ones((res['np'], 1))], t.T)
    res['nn'] = np.dot(np.c_[res['nn'], np.zeros((res['np'], 1))], t.T)
    return res


def invert_transform(trans):
    """
    %
    % [itrans] = fiff_invert_transform(trans)
    %
    % Invert a coordinate transformation
    %
    """
    itrans = copy.copy(trans)
    aux = itrans['from_']
    itrans['from_'] = itrans['to']
    itrans['to'] = aux
    itrans['trans'] = linalg.inv(itrans['trans'])
    return itrans


def read_named_matrix(fid, node, matkind):
    """
    %
    % [mat] = fiff_read_named_matrix(fid,node)
    %
    % Read named matrix from the given node
    %
    """

    #   Descend one level if necessary
    if node.block != FIFF.FIFFB_MNE_NAMED_MATRIX:
        for k in range(node.nchild):
            if node.children[k].block == FIFF.FIFFB_MNE_NAMED_MATRIX:
                if has_tag(node.children[k], matkind):
                    node = node.children[k]
                    break
        else:
            raise ValueError, 'Desired named matrix (kind = %d) not available' % matkind
    else:
       if not has_tag(node, matkind):
          raise ValueError, 'Desired named matrix (kind = %d) not available' % matkind

    #   Read everything we need
    tag = find_tag(fid, node, matkind)
    if tag is None:
       raise ValueError, 'Matrix data missing'
    else:
       data = tag.data;

    nrow, ncol = data.shape
    tag = find_tag(fid, node, FIFF.FIFF_MNE_NROW)
    if tag is not None:
       if tag.data != nrow:
          raise ValueError, 'Number of rows in matrix data and FIFF_MNE_NROW tag do not match'

    tag = find_tag(fid, node, FIFF.FIFF_MNE_NCOL)
    if tag is not None:
       if tag.data != ncol:
          raise ValueError, 'Number of columns in matrix data and FIFF_MNE_NCOL tag do not match'

    tag = find_tag(fid, node, FIFF.FIFF_MNE_ROW_NAMES)
    if tag is not None:
        row_names = tag.data.split(':')
    else:
        row_names = []

    tag = find_tag(fid, node, FIFF.FIFF_MNE_COL_NAMES)
    if tag is not None:
        col_names = tag.data.split(':')
    else:
        col_names = []

    mat = dict(nrow=nrow, ncol=ncol, row_names=row_names, col_names=col_names,
               data=data)
    return mat


def find_source_space_hemi(src):
    """
    %
    % function mne_find_source_space_hemi(src)
    %
    % Return the hemisphere id for a source space
    %
    % src      - The source space to investigate
    % hemi     - Deduced hemisphere id
    %
    """

    xave = src['rr'][:,0].sum();

    if xave < 0:
        hemi = int(FIFF.FIFFV_MNE_SURF_LEFT_HEMI)
    else:
        hemi = int(FIFF.FIFFV_MNE_SURF_RIGHT_HEMI)

    return hemi


def read_one(fid, node):
    """
    %
    %   Read all interesting stuff for one forward solution
    %
    """
    if node is None:
        return None

    tag = find_tag(fid, node, FIFF.FIFF_MNE_SOURCE_ORIENTATION)
    if tag is None:
        fid.close()
        raise ValueError, 'Source orientation tag not found'

    one = dict()
    one['source_ori'] = tag.data
    tag = find_tag(fid, node, FIFF.FIFF_MNE_COORD_FRAME)
    if tag is None:
        fid.close()
        raise ValueError, 'Coordinate frame tag not found'

    one['coord_frame'] = tag.data
    tag = find_tag(fid, node, FIFF.FIFF_MNE_SOURCE_SPACE_NPOINTS)
    if tag is None:
        fid.close()
        raise ValueError, 'Number of sources not found'

    one['nsource'] = tag.data
    tag = find_tag(fid, node, FIFF.FIFF_NCHAN)
    if tag is None:
        fid.close()
        raise ValueError, 'Number of channels not found'

    one['nchan'] = tag.data
    try:
        one['sol'] = read_named_matrix(fid, node, FIFF.FIFF_MNE_FORWARD_SOLUTION)
        one['sol'] = transpose_named_matrix(one['sol'])
    except Exception as inst:
        fid.close()
        raise 'Forward solution data not found (%s)' % inst

    try:
        one['sol_grad'] = read_named_matrix(fid,node,FIFF.FIFF_MNE_FORWARD_SOLUTION_GRAD)
        one['sol_grad'] = transpose_named_matrix(one['sol_grad'])
    except Exception as inst:
        one['sol_grad'] = None

    if one['sol']['data'].shape[0] != one['nchan'] or \
                (one['sol']['data'].shape[1] != one['nsource'] and
                 one['sol']['data'].shape[1] != 3*one['nsource']):
        fid.close()
        raise ValueError, 'Forward solution matrix has wrong dimensions'

    if one['sol_grad'] is not None:
        if one['sol_grad']['data'].shape[0] != one['nchan'] or \
                (one['sol_grad']['data'].shape[1] != 3*one['nsource'] and
                 one['sol_grad']['data'].shape[1] != 3*3*one['nsource']):
           fid.close()
           raise ValueError, 'Forward solution gradient matrix has wrong dimensions'

    return one


def read_forward_solution(fname, force_fixed=False, surf_ori=False,
                              include=None, exclude=None):
    """
    %
    % [fwd] = mne_read_forward_solution(fname,force_fixed,surf_ori,include,exclude)
    %
    % A forward solution from a fif file
    %
    % fname        - The name of the file
    % force_fixed  - Force fixed source orientation mode? (optional)
    % surf_ori     - Use surface based source coordinate system? (optional)
    % include      - Include these channels (optional)
    % exclude      - Exclude these channels (optional)
    %
    """

    #   Open the file, create directory
    print 'Reading forward solution from %s...' % fname
    fid, tree, _ = fiff_open(fname)

    #   Find all forward solutions
    fwds = dir_tree_find(tree, FIFF.FIFFB_MNE_FORWARD_SOLUTION)
    if len(fwds) == 0:
        fid.close()
        raise ValueError, 'No forward solutions in %s' % fname

    #   Parent MRI data
    parent_mri = dir_tree_find(tree,FIFF.FIFFB_MNE_PARENT_MRI_FILE)
    if len(fwds) == 0:
        fid.close()
        raise ValueError, 'No parent MRI information in %s' % fname
    parent_mri = parent_mri[0]

    try:
        src = read_source_spaces(fid, False, tree)
    except Exception as inst:
        fid.close()
        raise ValueError, 'Could not read the source spaces (%s)' % inst

    for s in src:
       s['id'] = find_source_space_hemi(s)

    fwd = None

    #   Bad channel list
    bads = read_bad_channels(fid, tree)

    print '\t%d bad channels read' % len(bads)

    #   Locate and read the forward solutions
    megnode = None
    eegnode = None
    for k in range(len(fwds)):
        tag = find_tag(fid, fwds[k], FIFF.FIFF_MNE_INCLUDED_METHODS)
        if tag is None:
            fid.close()
            raise ValueError, 'Methods not listed for one of the forward solutions'

        if tag.data == FIFF.FIFFV_MNE_MEG:
            megnode = fwds[k]
        elif tag.data == FIFF.FIFFV_MNE_EEG:
            eegnode = fwds[k]

    megfwd = read_one(fid, megnode)
    if megfwd is not None:
        if megfwd['source_ori'] == FIFF.FIFFV_MNE_FIXED_ORI:
            ori = 'fixed'
        else:
            ori = 'free'

        print '\tRead MEG forward solution (%d sources, %d channels, %s orientations)' % (
                                    megfwd['nsource'], megfwd['nchan'], ori)

    eegfwd = read_one(fid, eegnode)
    if eegfwd is not None:
        if eegfwd['source_ori'] == FIFF.FIFFV_MNE_FIXED_ORI:
            ori = 'fixed'
        else:
            ori = 'free'

        print '\tRead EEG forward solution (%d sources, %d channels, %s orientations)' % (
                                    eegfwd['nsource'], eegfwd['nchan'], ori)

    #   Merge the MEG and EEG solutions together
    if megfwd is not None and eegfwd is not None:
        if (megfwd['sol']['data'].shape[1] != eegfwd['sol']['data'].shape[1] or 
                megfwd['source_ori'] != eegfwd['source_ori'] or
                megfwd['nsource'] != eegfwd['nsource'] or
                megfwd['coord_frame'] != eegfwd['coord_frame']):
            fid.close()
            raise ValueError, 'The MEG and EEG forward solutions do not match'

        fwd = megfwd
        fwd['sol']['data'] = np.r_[fwd['sol']['data'], eegfwd['sol']['data']]
        fwd['sol']['nrow'] = fwd['sol']['nrow'] + eegfwd['sol']['nrow'];

        fwd['sol']['row_names'] = fwd['sol']['row_names'] + eegfwd['sol']['row_names']
        if fwd['sol_grad'] is not None:
            fwd['sol_grad']['data'] = np.r_[fwd['sol_grad']['data'], eegfwd['sol_grad']['data']]
            fwd['sol_grad']['nrow'] = fwd['sol_grad']['nrow'] + eegfwd['sol_grad']['nrow']
            fwd['sol_grad']['row_names'] = fwd['sol_grad']['row_names'] + eegfwd['sol_grad']['row_names']

        fwd['nchan'] = fwd['nchan'] + eegfwd['nchan']
        print '\tMEG and EEG forward solutions combined'
    elif megfwd is not None:
        fwd = megfwd;
    else:
        fwd = eegfwd;

    del megfwd
    del eegfwd

    #   Get the MRI <-> head coordinate transformation
    tag = find_tag(fid, parent_mri, FIFF.FIFF_COORD_TRANS)
    if tag is None:
        fid.close()
        raise ValueError, 'MRI/head coordinate transformation not found'
    else:
        mri_head_t = tag.data;
        if (mri_head_t['from_'] != FIFF.FIFFV_COORD_MRI or
                mri_head_t['to'] != FIFF.FIFFV_COORD_HEAD):
            mri_head_t = invert_transform(mri_head_t)
            if (mri_head_t['from_'] != FIFF.FIFFV_COORD_MRI
                or mri_head_t['to'] != FIFF.FIFFV_COORD_HEAD):
                fid.close()
                raise ValueError, 'MRI/head coordinate transformation not found'

    fid.close()

    fwd['mri_head_t'] = mri_head_t;

    #   Transform the source spaces to the correct coordinate frame
    #   if necessary

    if (fwd['coord_frame'] != FIFF.FIFFV_COORD_MRI and
            fwd['coord_frame'] != FIFF.FIFFV_COORD_HEAD):
        raise ValueError, 'Only forward solutions computed in MRI or head coordinates are acceptable'

    nuse = 0
    for s in src:
       try:
          s = transform_source_space_to(s, fwd['coord_frame'], mri_head_t)
       except Exception as inst:
          raise ValueError, 'Could not transform source space (%s)' % inst

       nuse += s['nuse']

    if nuse != fwd['nsource']:
        raise ValueError, 'Source spaces do not match the forward solution.'

    print '\tSource spaces transformed to the forward solution coordinate frame'
    fwd['src'] = src;

    #   Handle the source locations and orientations
    if fwd['source_ori'] == FIFF.FIFFV_MNE_FIXED_ORI or force_fixed == True:
        nuse = 0
        fwd['source_rr'] = np.zeros((fwd['nsource'], 3))
        fwd['source_nn'] = np.zeros((fwd['nsource'], 3))
        for s in src:
            fwd['source_rr'][nuse:nuse+s['nuse'],:] = s['rr'][s['vertno'],:]
            fwd['source_nn'][nuse:nuse+s['nuse'],:] = s['nn'][s['vertno'],:]
            nuse += s['nuse']

        #   Modify the forward solution for fixed source orientations
        if fwd['source_ori'] != FIFF.FIFFV_MNE_FIXED_ORI:
            print '\tChanging to fixed-orientation forward solution...'
            fix_rot = block_diag(fwd['source_nn'].T, 1)
            fwd['sol']['data'] *= fix_rot
            fwd['sol']['ncol'] = fwd['nsource']
            fwd['source_ori'] = FIFF.FIFFV_MNE_FIXED_ORI

            if fwd['sol_grad'] is not None:
               fwd['sol_grad']['data'] = np.dot(fwd['sol_grad']['data'], np.kron(fix_rot, np.eye(3)))
               fwd['sol_grad']['ncol'] = 3*fwd['nsource']

            print '[done]'
    else:
        if surf_ori:
            #   Rotate the local source coordinate systems
            print '\tConverting to surface-based source orientations...'
            nuse = 0
            pp = 1
            fwd['source_rr'] = np.zeros(fwd['nsource'], 3)
            for s in src:
                fwd['source_rr'][nuse+1:nuse + s['nuse'],:] = s['rr'][s['vertno'],:]
                for p in range(s['nuse']):
                    #  Project out the surface normal and compute SVD
                    nn = s['nn'][s['vertno'][p],:].T
                    nn = nn[:,None]
                    [ U, S, V ]  = linalg.svd(np.eye(3,3) - nn*nn.T)
                    #  Make sure that ez is in the direction of nn
                    if np.sum(nn*U[:,2]) < 0:
                        U *= -1
                        fwd['source_nn'][pp:pp+2,:] = U.T
                        pp += 3
                    nuse += s['nuse']

            surf_rot = block_diag(fwd['source_nn'].T, 3)
            fwd['sol']['data'] = np.dot(fwd['sol']['data'], surf_rot)
            if fwd['sol_grad'] is not None:
                fwd['sol_grad']['data'] = np.dot(fwd['sol_grad']['data'] * np.kron(surf_rot, np.eye(3)))

            print '[done]'
        else:
            print '\tCartesian source orientations...'
            nuse = 0
            fwd['source_rr'] = np.zeros((fwd['nsource'], 3))
            for s in src:
                fwd['source_rr'][nuse:nuse+s['nuse'],:] = s['rr'][s['vertno'],:]
                nuse += s['nuse']

            fwd['source_nn'] = np.kron(np.ones((fwd['nsource'], 1)), np.eye(3));
            print '[done]'

    #   Do the channel selection
    if include is not None or exclude is not None or bads is not None:
        #   First do the channels to be included
        pick = np.ones(fwd['nchan'], dtype=np.bool)
        if include is not None:
            for p in range(len(fwd['sol']['row_names'])):
                if fwd['sol']['row_names'][p] in include:
                    pick[p] = True

        #   Then exclude what needs to be excluded
        if exclude is not None:
            for p in range(len(fwd['sol']['row_names'])):
                if fwd['sol']['row_names'][p] in exclude:
                    pick[p] = False

        if bads is not None:
            for k in range(len(bads)):
                for p in range(len(fwd['sol']['row_names'])):
                    if fwd['sol']['row_names'][p] in bads:
                        pick[p] = False

        #   Do we have something?
        nuse = pick.sum();
        if nuse == 0:
            raise ValueError, 'Nothing remains after picking'

        print '\t%d out of %d channels remain after picking\n' % (nuse, fwd['nchan'])

        #   Pick the correct rows of the forward operator
        fwd['nchan'] = nuse
        fwd['sol']['data'] = fwd['sol']['data'][pick == 1,:]
        fwd['sol']['nrow'] = nuse
        fwd['sol']['row_names'] = [fwd['sol']['row_names'][k]
                                    for k in range(len(pick)) if pick[k]]

        if fwd['sol_grad'] is not None:
            fwd['sol_grad']['data'] = fwd['sol_grad']['data'][pick == 1, :]
            fwd['sol_grad']['nrow'] = nuse
            fwd['sol_grad']['row_names'] = [fwd['sol_grad']['row_names'][k]
                                            for k in range(len(pick)) if pick[k]]

    return fwd