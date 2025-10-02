import os
from robot.api import logger
from robot.api.deco import keyword
import git

class GitOperations(object):

    def __init__(self):
        self._project_name = str(os.environ.get("SCRIPTS"))
        logger.console(f'project: {self._project_name}')
        # Execution path is different in normal test runs and in Live Testing,
        # and we need to take that into account
        self._project_path = os.getcwd()
        logger.console(f'path: {self._project_path}')
        # SCRIPTS env variable contains the suite name (except locally)
        if self._project_name != "None":
            if self._project_path == "/home/services/suite/tests":
                # We are in live testing and project name is not in project path
                self._project_path = os.path.join("/home/services/suite/")
            else:
                self._project_path = os.path.join(os.getcwd(), self._project_name)

        logger.console(self._project_path)
        self._data_path = os.path.join(self._project_path, "files/")
        logger.console(self._data_path)

    @keyword
    def commit_and_push(self, file_name, git_branch):

        path_to_file = os.path.join(self._data_path, file_name)

        # Repo exists in project path
        my_repo = git.Repo(self._project_path)

        # Print git status to console for visibility
        logger.console("\n" + my_repo.git.status() + "\n")

        # Add, commit and push to git
        my_repo.index.add(path_to_file)
        my_repo.index.commit("CRT robot committing changes to {}".format(file_name))
        my_repo.git.push("origin", git_branch)
