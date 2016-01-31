#!/usr/bin/env python3

import time
import uuid
import functools
import threading
import statistics
import requests
import sys
from concurrent import futures

def get_ac_auth(path_crt, path_key, obj_perm, obj_type, obj_uid=None):

    url = "https://ac.tutamen-test.bdr1.volaticus.net/api/v1/authorizations/"

    json = {'objperm': obj_perm,
            'objtype': obj_type,
            'objuid': str(obj_uid) if obj_uid else ""}

    res = requests.post(url=url, json=json, cert=(path_crt, path_key))
    res.raise_for_status()
    uid = res.json()['authorizations'][0]
    return uid

def get_ac_token(path_crt, path_key, uid):

    url = "https://ac.tutamen-test.bdr1.volaticus.net/api/v1/authorizations/"
    url += str(uid) + "/"

    res = requests.get(url=url, cert=(path_crt, path_key))
    res.raise_for_status()
    authz = res.json()
    return authz['token']

def get_ss_secret(token, col_uid, sec_uid):

    url = "https://ss.tutamen-test.bdr1.volaticus.net/api/v1/"
    url += "/collections/" + str(col_uid)
    url += "/secrets/" + str(sec_uid)
    url += "/versions/latest/"

    header = {'tutamen-tokens': token}
    res = requests.get(url=url, headers=header)
    res.raise_for_status()
    authz = res.json()
    return authz['data']

def get_ac_null_cert(path_crt, path_key):

    url = "https://ac.tutamen-test.bdr1.volaticus.net/api/v1/"
    res = requests.get(url=url, cert=(path_crt, path_key))
    res.raise_for_status()

def get_ac_null():

    url = "https://ac.tutamen-test.bdr1.volaticus.net/api/v1/"
    res = requests.get(url=url)
    res.raise_for_status()

def get_ss_null():

    url = "https://ss.tutamen-test.bdr1.volaticus.net/api/v1/"
    res = requests.get(url=url)
    res.raise_for_status()

def res_time():

    def _decorator(func):

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):

            start = time.time()
            func(*args, **kwargs)
            dur = time.time() - start
            return dur

        return _wrapper

    return _decorator

def min_time(sec):

    def _decorator(func):

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):

            start = time.time()
            ret = func(*args, **kwargs)
            dur = time.time() - start
            if dur < sec:
                time.sleep(sec-dur)
            return ret

        return _wrapper

    return _decorator

def benchmark(iops_start, iops_end, iops_step, duration, function, *args, **kwargs):

    min_t = 2 #second

    @res_time()
    def bm_function(*bm_args, **bm_kwargs):

        try:
            function(*bm_args, **bm_kwargs)
        except Exception as error:
            print(error)

    for iops_target in range(iops_start, iops_end, iops_step):

        threads = iops_target * min_t
        cnt = iops_target * duration
        pause = 1.0 / iops_target

        futrs = []
        times = []
        start = time.time()
        with futures.ThreadPoolExecutor(max_workers=threads) as e:
            for i in range(0, cnt):
                run_t_actual = time.time() - start
                run_t_target = i * pause
                if run_t_actual < run_t_target:
                    time.sleep(run_t_target - run_t_actual)
                futrs.append(e.submit(bm_function, *args, **kwargs))
            for f in futrs:
                times.append(f.result())

        tot = time.time() - start
        iops = (float(cnt) / float(tot))
        avg = statistics.mean(times)
        std = statistics.pstdev(times)
        print("{}, {:.1f}, {:.1f}, {:.3f}, {:.3f}".format(cnt, tot, iops, avg, std))

if __name__ == "__main__":

    path_crt = sys.argv[1]
    path_key = sys.argv[2]
    iops_start = int(sys.argv[3])
    iops_end = int(sys.argv[4])
    iops_step = int(sys.argv[5])
    duration = int(sys.argv[6])
    test = sys.argv[7]


    if test == "get_ss_null":
        benchmark(iops_start, iops_end, iops_step, duration,
                  get_ss_null)

    elif test == "get_ac_null":
        benchmark(iops_start, iops_end, iops_step, duration,
                  get_ac_null)

    elif test == "get_ac_null_cert":
        benchmark(iops_start, iops_end, iops_step, duration,
                  get_ac_null_cert, path_crt, path_key)

    elif test == "get_ac_auth":
        benchmark(iops_start, iops_end, iops_step, duration,
                  get_ac_auth, path_crt, path_key, "create", "storageserver")

    elif test == "get_ss_secret":
        
        col_uid = uuid.UUID(sys.argv[8])
        sec_uid = uuid.UUID(sys.argv[9])

        auth_uid = get_ac_auth(path_crt, path_key,
                               "read", "collection", col_uid)
        token = get_ac_token(path_crt, path_key, auth_uid)

        benchmark(iops_start, iops_end, iops_step, duration,
                  get_ss_secret, token, col_uid, sec_uid)

    else:
        print("Unrecognized test case")
