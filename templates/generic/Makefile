clean:
	rm -rf {{ WORKING_DIR_BASENAME}}
	mkdir -p {{ WORKING_DIR_BASENAME}}/{{ SESSION }}/processing/

get: clean
	./{{ SCRIPTNAME_GET }}.sh

process: get
	./{{ SCRIPTNAME_PROCESS }}.sh
