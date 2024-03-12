import json


def load_lockup(path, mapping):
    files = {}
    for x in mapping:
        ldn = mapping[x].split(".")[0]
        with open(f"{path}/{mapping[x]}", "rb") as fb:
            files[ldn] = json.load(fb)
    # with open(f"{path}/test_{mapping[x]}", "w") as fb:
    #     json.dump(files, fb)
    return files


def load_base(fn):
    with open(fn, "rb") as fb:
        data = json.load(fb)
    return data


def denormalize_json(fn, path, mapping):
    save_and_open = f"{path}/{fn}.json"
    print(f"updating {save_and_open}")
    # load mapping file
    mpg = mapping
    # load lockup file to match with
    files = load_lockup(path, mpg)
    # load base json file for matching
    dta = load_base(save_and_open)
    for m in mpg:
        # if mapping key is found in base json
        for d in dta:
            if dta[d][m]:
                # get filename without ext
                ldn = mpg[m].split(".")[0]
                # get specific mapping from lockup file
                lockup = files[ldn]
                # iterate over mapping entity array
                for i in dta[d][m]:
                    i_id = i["id"]
                    # use id for lockup file
                    i_upt = lockup[str(i_id)]
                    # create normalized data
                    norm = {n: i_upt[n] for n in i_upt
                            if not isinstance(i_upt[n], list) and n != "id" and n != "order"}
                    i["data"] = norm
                    i["data"]["filename"] = mpg[m]
    with open(f"{path}/{fn}_denormalized.json", "w") as w:
        json.dump(dta, w)
    print(f"finished update of {save_and_open} and save as {save_and_open}.")
    return dta
