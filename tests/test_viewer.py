import unittest

from src.bindecoder.viewer import DataViewer, PathViewer

class TestData(unittest.TestCase):
    def setUp(self):
        self.data = {'vars': [
            {'type': 'int', 'value': 42},
            {'type': 'struct', 'value': {
                'foo': {'bar': {'baz': 99, 'quux': 1.25}}}},
            {'type': 'list', 'value': [3,14]}
        ]}

    def test_data(self):
        view = DataViewer()
        self.traverse(view)
        self.assertEqual(view.result(), self.data)

    def test_path(self):
        data = DataViewer()
        path = PathViewer('vars/1/value/foo', data)
        self.traverse(path)
        self.assertEqual(path.result(), self.data['vars'][1]['value']['foo'])

    def traverse(self, view):
        with view.array('vars'):
            with view.map(0):
                view.set('type', 'int')
                view.set('value', 42)
            with view.map(1):
                view.set('type', 'struct')
                with view.map('value'):
                    with view.map('foo'):
                        with view.map('bar'):
                            view.set('baz', 99)
                            view.set('quux', 1.25)
            with view.map(2):
                view.set('type', 'list')
                with view.array('value'):
                    view.set(0, 3)
                    view.set(1, 14)

if __name__=='__main__':
    unittest.main()

        
