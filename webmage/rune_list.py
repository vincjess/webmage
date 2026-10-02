class RuneList(list):
    def __init__(self, iterable):
        super().__init__(item for item in iterable)

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(key)
        elif isinstance(key, str):
            return_list = []
            for i in self:
                if key in i:
                    return_list.append(i[key])
                else:
                    return_list.append(None)
            return return_list


    def __repr__(self):
        tags = ', '.join(f'<{i.name}>' for i in self)
        return f'[{tags}]'
    

    def __str__(self):
        tags = ', '.join(f'<{i.tagName}>' for i in self)
        return f'[{tags}]'
