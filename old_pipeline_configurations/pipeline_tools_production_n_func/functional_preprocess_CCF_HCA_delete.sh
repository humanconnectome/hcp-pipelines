module load singularity-3.2.1

SubjectFile=${HOME}/pipeline_tools_production_n_func/xnat_pbs_jobs_control_CCF_HCA/failing.subjects

source $HOME/processing/pipeline_tools_production_n_func/xnat_pbs_jobs_control_CCF_HCA/xnat_pbs_setup intradb

for line in $(cat $SubjectFile) ; do
	[[ "$line" =~ ^# ]] && continue
    #echo $line
	IFS=':' read -ra subject <<< "$line"
	echo "Removing running status : " ${subject[0]} ${subject[1]} ${subject[2]} ${subject[3]}

	singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd \
	/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT.sif \
	/pipeline_tools/xnat_pbs_jobs/FunctionalPreprocessing/FunctionalPreprocessing.XNAT_MARK_RUNNING_STATUS \
	--user="junilc" \
	--password="Aa123456" \
	--server="10.28.58.65:8080" \
	--project="${subject[0]}" \
	--subject="${subject[1]}" \
	--classifier="${subject[2]}" \
	--scan="${subject[3]}" \
	--resource="RunningStatus" \
	--done

done

